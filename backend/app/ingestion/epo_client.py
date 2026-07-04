"""
EPO Open Patent Services (OPS) Client.

Implements OAuth2 authentication and patent data retrieval from EPO.
EPO OPS publishes new patents on Wednesdays.

Rate limits (free tier):
- 4GB/week data transfer
- 10 searches/minute
- 200 retrieval requests/minute

Requires EPO_OPS_CLIENT_ID and EPO_OPS_CLIENT_SECRET.
Register at: https://developers.epo.org/
"""

import base64
import logging
from collections.abc import Iterator
from datetime import date, datetime, timedelta

import httpx

from app.config import settings
from app.core.exceptions import IngestionError, TransientIngestionError

logger = logging.getLogger(__name__)

EPO_AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
EPO_API_BASE = "https://ops.epo.org/3.2/rest-services"

TOKEN_REFRESH_BUFFER_SECONDS = 300


async def _epo_source_fetch(
    target_type: str,
    target_id: str | None = None,
    status: str = "success",
    http_status: int | None = None,
    error_message: str | None = None,
    records_found: int | None = None,
    duration_ms: int | None = None,
):
    """Fire-and-forget source_fetch recording for EPO API calls."""
    try:
        from app.ingestion.source_fetch import record_source_fetch_async
        await record_source_fetch_async(
            provider="epo_ops",
            office="EP",
            target_type=target_type,
            target_id=target_id,
            status=status,
            http_status=http_status,
            error_message=error_message,
            records_found=records_found,
            duration_ms=duration_ms,
        )
    except Exception:
        logger.debug("Failed to record EPO source fetch", exc_info=True)


class EPOClient:
    """
    Client for fetching patent data from EPO Open Patent Services.

    Uses OAuth2 client credentials flow for authentication.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.client_id = client_id or settings.epo_ops_client_id
        self.client_secret = client_secret or settings.epo_ops_client_secret

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "EPO OPS credentials not configured. "
                "Set EPO_OPS_CLIENT_ID and EPO_OPS_CLIENT_SECRET."
            )

        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._http_client = httpx.Client(timeout=30.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._http_client.close()

    def _get_access_token(self) -> str:
        """Get or refresh OAuth2 access token."""
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at - timedelta(
                seconds=TOKEN_REFRESH_BUFFER_SECONDS
            ):
                return self._access_token

        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        try:
            response = self._http_client.post(
                EPO_AUTH_URL,
                headers={
                    "Authorization": f"Basic {encoded_credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
            response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = int(token_data.get("expires_in", 1200))
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("EPO OPS access token refreshed")
            return self._access_token

        except httpx.HTTPStatusError as e:
            logger.error(f"EPO auth failed: {e}")
            raise IngestionError(f"EPO authentication failed: {e}") from e
        except Exception as e:
            logger.error(f"EPO auth error: {e}")
            raise TransientIngestionError(f"EPO auth error: {e}") from e

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        accept: str = "application/json",
    ) -> dict:
        """Make authenticated request to EPO OPS API."""
        token = self._get_access_token()

        url = f"{EPO_API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": accept,
        }

        try:
            response = self._http_client.request(
                method,
                url,
                params=params,
                headers=headers,
            )

            if response.status_code == 403:
                raise IngestionError(
                    "EPO rate limit exceeded or access forbidden. "
                    "Check your quota at https://developers.epo.org/"
                )

            response.raise_for_status()

            if "application/json" in response.headers.get("content-type", ""):
                return response.json()
            return {"raw": response.text}

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (500, 502, 503, 504):
                raise TransientIngestionError(f"EPO server error: {e}") from e
            raise IngestionError(f"EPO request failed: {e}") from e
        except httpx.RequestError as e:
            raise TransientIngestionError(f"EPO connection error: {e}") from e

    def fetch_abstract_for_us_patent(self, us_publication_number: str) -> str | None:
        """
        Fetch the abstract for a US patent via EPO OPS.

        Args:
            us_publication_number: US publication number (e.g., "12586484")

        Returns:
            Abstract text or None if not found.
        """
        clean_number = us_publication_number.replace(",", "").strip()
        epodoc_id = f"US{clean_number}"

        try:
            path = f"/published-data/publication/epodoc/{epodoc_id}/abstract"
            result = self._request("GET", path)

            wpd = result.get("ops:world-patent-data", {})
            ed = wpd.get("exchange-documents", wpd.get("exchange-document", {}))
            if isinstance(ed, list):
                ed = ed[0] if ed else {}
            doc = ed.get("exchange-document", ed)

            return self._extract_abstract(doc)

        except IngestionError as e:
            if "404" in str(e) or "Not Found" in str(e):
                logger.debug(f"No abstract found for {epodoc_id}")
                return None
            logger.warning(f"EPO abstract fetch failed for {epodoc_id}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error fetching abstract for {epodoc_id}: {e}")
            return None

    def fetch_claims_for_us_patent(self, us_publication_number: str) -> str | None:
        """
        Fetch the claims text for a US patent via EPO OPS.

        Args:
            us_publication_number: US publication number (e.g., "12586484")

        Returns:
            Claims text or None if not found.
        """
        clean_number = us_publication_number.replace(",", "").strip()
        epodoc_id = f"US{clean_number}"

        try:
            path = f"/published-data/publication/epodoc/{epodoc_id}/claims"
            result = self._request("GET", path)

            wpd = result.get("ops:world-patent-data", {})
            ft = wpd.get("ftxt:fulltext-documents", wpd.get("fulltext-documents", {}))
            if not ft:
                return None

            ftdoc = ft.get("ftxt:fulltext-document", ft.get("fulltext-document", {}))
            if isinstance(ftdoc, list):
                ftdoc = ftdoc[0] if ftdoc else {}

            claims = ftdoc.get("claims", {})
            if isinstance(claims, list):
                claims = claims[0] if claims else {}

            claim_list = claims.get("claim", [])
            if isinstance(claim_list, dict):
                claim_list = [claim_list]

            texts = []
            for claim in claim_list:
                claim_text = claim.get("claim-text", [])
                if isinstance(claim_text, str):
                    texts.append(claim_text)
                elif isinstance(claim_text, dict):
                    texts.append(claim_text.get("$", ""))
                elif isinstance(claim_text, list):
                    for ct in claim_text:
                        if isinstance(ct, str):
                            texts.append(ct)
                        elif isinstance(ct, dict):
                            texts.append(ct.get("$", ""))

            return "\n\n".join(t for t in texts if t) if texts else None

        except IngestionError as e:
            if "404" in str(e) or "Not Found" in str(e):
                logger.debug(f"No claims found for {epodoc_id}")
                return None
            logger.warning(f"EPO claims fetch failed for {epodoc_id}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error fetching claims for {epodoc_id}: {e}")
            return None

    def fetch_fulltext_for_us_patent(self, us_publication_number: str) -> dict:
        """
        Fetch abstract and claims for a US patent via EPO OPS.
        Makes separate API calls for abstract and claims.

        Args:
            us_publication_number: US publication number (e.g., "12586484")

        Returns:
            Dict with 'abstract' and 'claims_text' keys (values may be None).
        """
        result = {
            "abstract": self.fetch_abstract_for_us_patent(us_publication_number),
            "claims_text": self.fetch_claims_for_us_patent(us_publication_number),
        }
        return result

    def fetch_publication(self, publication_number: str) -> dict:
        """
        Fetch bibliographic data for a single publication.

        Args:
            publication_number: EP publication number (e.g., "EP1234567A1")

        Returns:
            Raw publication data dictionary
        """
        import asyncio
        path = f"/published-data/publication/epodoc/{publication_number}/biblio"
        result = self._request("GET", path)
        try:
            asyncio.ensure_future(
                _epo_source_fetch(
                    target_type="publication",
                    target_id=publication_number,
                    status="success",
                    records_found=1,
                )
            )
        except RuntimeError:
            pass
        return result

    def fetch_drawings(self, publication_number: str) -> list[bytes]:
        """Fetch patent drawings/images from EPO OPS published-images API.

        Args:
            publication_number: EPODOC-format number (e.g., 'US12586484B2').

        Returns:
            List of raw image bytes (may be TIFF). Empty list if none found.
        """
        clean = publication_number.replace("-", "").replace("/", "").strip()
        path = f"/published-data/images/{clean}/drawings"
        try:
            result = self._request("GET", path, accept="application/tiff")
            # OPS returns a multi-page TIFF. Split into individual pages.
            pages = self._split_tiff_pages(result)
            return pages
        except IngestionError as e:
            if "404" in str(e) or "Not Found" in str(e):
                logger.debug("No drawings found for %s", clean)
                return []
            raise
        except Exception as e:
            logger.warning("Drawings fetch failed for %s: %s", clean, e)
            return []

    @staticmethod
    def _split_tiff_pages(result: dict) -> list[bytes]:
        """Split multi-page TIFF response into individual page bytes.

        EPO OPS returns either a single TIFF with multiple pages or a
        multipart response. Extract each page into its own byte buffer.
        """
        import io

        from PIL import Image

        raw = result.get("raw", "")
        if not raw or not isinstance(raw, str):
            return []

        # The raw response may be base64-encoded or binary text
        try:
            import base64
            data = base64.b64decode(raw)
        except Exception:
            # Try treating as latin-1 encoded binary
            data = raw.encode("latin-1")

        pages: list[bytes] = []
        try:
            img = Image.open(io.BytesIO(data))
            page_idx = 0
            while True:
                buf = io.BytesIO()
                img.seek(page_idx)
                img.save(buf, format="TIFF")
                pages.append(buf.getvalue())
                page_idx += 1
        except EOFError:
            pass  # no more pages
        except Exception:
            # Single page or non-TIFF — return as single page
            try:
                img = Image.open(io.BytesIO(data))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                pages = [buf.getvalue()]
            except Exception:
                pages = [data]

        return pages

    def fetch_publications_by_date(self, publication_date: date) -> Iterator[dict]:
        """
        Fetch all EP publications for a specific date.

        Args:
            publication_date: The publication date (typically a Wednesday)

        Yields:
            Raw publication data dictionaries
        """
        date_str = publication_date.strftime("%Y%m%d")
        logger.info(f"Fetching EPO publications for {publication_date}")

        range_begin = 1
        range_end = 100

        while True:
            path = "/published-data/search/full-cycle"
            params = {
                "q": f'pd="{date_str}"',
                "Range": f"{range_begin}-{range_end}",
            }

            try:
                import asyncio
                import time as _time
                _start = _time.monotonic()
                response = self._request("GET", path, params=params)
                _duration = int((_time.monotonic() - _start) * 1000)
                publications = self._extract_publications(response)

                # Record source_fetch for this page
                try:
                    asyncio.ensure_future(_epo_source_fetch(
                        target_type="search_by_date",
                        target_id=date_str,
                        status="success",
                        records_found=len(publications),
                        duration_ms=_duration,
                    ))
                except RuntimeError:
                    pass

                if not publications:
                    break

                for pub in publications:
                    yield pub

                if len(publications) < (range_end - range_begin + 1):
                    break

                range_begin = range_end + 1
                range_end = range_begin + 99

            except IngestionError:
                import asyncio as _aio
                try:
                    _aio.ensure_future(_epo_source_fetch(
                        target_type="search_by_date",
                        target_id=date_str,
                        status="failed",
                    ))
                except RuntimeError:
                    pass
                break

    def fetch_family(self, publication_number: str) -> dict:
        """
        Fetch INPADOC family data for a publication.

        Args:
            publication_number: Publication number

        Returns:
            Family data including all family members
        """
        path = f"/family/publication/epodoc/{publication_number}"
        return self._request("GET", path)

    def fetch_legal_status(self, publication_number: str) -> dict:
        """
        Fetch legal status events for a publication.

        Args:
            publication_number: Publication number

        Returns:
            Legal status events
        """
        path = f"/legal/publication/epodoc/{publication_number}"
        return self._request("GET", path)

    def _extract_publications(self, response: dict) -> list[dict]:
        """Extract publication records from search response."""
        try:
            search_result = response.get("ops:world-patent-data", {}).get(
                "ops:biblio-search", {}
            )
            search_result = search_result.get("ops:search-result", {})
            publications = search_result.get("exchange-documents", [])

            if isinstance(publications, dict):
                publications = [publications]

            results = []
            for pub in publications:
                doc = pub.get("exchange-document", {})
                # exchange-document can be a single dict or a list of dicts
                if isinstance(doc, list):
                    for d in doc:
                        results.append(self._normalize_biblio(d))
                elif doc:
                    results.append(self._normalize_biblio(doc))

            return results

        except Exception as e:
            logger.warning(f"Failed to extract publications: {e}")
            return []

    def _normalize_biblio(self, doc: dict) -> dict:
        """Normalize EPO bibliographic data to common format."""
        biblio = doc.get("bibliographic-data", {})

        publication_ref = biblio.get("publication-reference", {}).get(
            "document-id", {}
        )
        if isinstance(publication_ref, list):
            publication_ref = publication_ref[0] if publication_ref else {}

        application_ref = biblio.get("application-reference", {}).get(
            "document-id", {}
        )
        if isinstance(application_ref, list):
            application_ref = application_ref[0] if application_ref else {}

        return {
            "publication_number": self._extract_doc_number(publication_ref),
            "application_number": self._extract_doc_number(application_ref),
            "kind_code": publication_ref.get("kind", {}).get("$", ""),
            "publication_date": publication_ref.get("date", {}).get("$", ""),
            "filing_date": application_ref.get("date", {}).get("$", ""),
            "title": self._extract_title(biblio),
            "abstract": self._extract_abstract(doc),
            "applicants": self._extract_parties(biblio, "applicants"),
            "inventors": self._extract_parties(biblio, "inventors"),
            "cpc_codes": self._extract_classifications(biblio, "classifications-cpc"),
            "ipc_codes": self._extract_classifications(biblio, "classifications-ipcr"),
            "priority_claims": self._extract_priorities(biblio),
            "raw_data": doc,
        }

    def _extract_doc_number(self, doc_ref: dict) -> str:
        """Extract document number from reference."""
        country = doc_ref.get("country", {}).get("$", "")
        doc_number = doc_ref.get("doc-number", {}).get("$", "")
        kind = doc_ref.get("kind", {}).get("$", "")
        return f"{country}{doc_number}{kind}".strip()

    def _extract_title(self, biblio: dict) -> str | None:
        """Extract English title."""
        titles = biblio.get("invention-title", [])
        if isinstance(titles, dict):
            titles = [titles]
        for title in titles:
            if title.get("@lang") == "en":
                return title.get("$")
        if titles:
            return titles[0].get("$")
        return None

    def _extract_abstract(self, doc: dict) -> str | None:
        """Extract English abstract."""
        abstracts = doc.get("abstract", [])
        if isinstance(abstracts, dict):
            abstracts = [abstracts]
        for abstract in abstracts:
            if abstract.get("@lang") == "en":
                paragraphs = abstract.get("p", [])
                if isinstance(paragraphs, dict):
                    paragraphs = [paragraphs]
                return " ".join(p.get("$", "") for p in paragraphs if p.get("$"))
        return None

    def _extract_parties(self, biblio: dict, party_type: str) -> list[dict]:
        """Extract applicants or inventors."""
        parties_data = biblio.get("parties", {}).get(party_type, {})
        party_list = parties_data.get(party_type[:-1], [])

        if isinstance(party_list, dict):
            party_list = [party_list]

        results = []
        for party in party_list:
            name_data = party.get(f"{party_type[:-1]}-name", {})
            if isinstance(name_data, dict):
                name = name_data.get("name", {}).get("$", "")
            else:
                name = str(name_data)
            if name:
                results.append({"name": name})

        return results

    def _extract_classifications(self, biblio: dict, cls_type: str) -> list[dict]:
        """Extract CPC or IPC classifications."""
        cls_data = biblio.get("patent-classifications", {}).get(cls_type, {})
        if not cls_data:
            cls_data = biblio.get(cls_type, {})

        cls_list = cls_data.get("classification-cpc", []) or cls_data.get(
            "classification-ipcr", []
        )

        if isinstance(cls_list, dict):
            cls_list = [cls_list]

        results = []
        for cls in cls_list:
            section = cls.get("section", {}).get("$", "")
            cls_class = cls.get("class", {}).get("$", "")
            subclass = cls.get("subclass", {}).get("$", "")
            main_group = cls.get("main-group", {}).get("$", "")
            subgroup = cls.get("subgroup", {}).get("$", "")

            code = f"{section}{cls_class}{subclass} {main_group}/{subgroup}".strip()
            if code:
                results.append({"code": code})

        return results

    def _extract_priorities(self, biblio: dict) -> list[dict]:
        """Extract priority claims."""
        priority_claims = biblio.get("priority-claims", {}).get("priority-claim", [])
        if isinstance(priority_claims, dict):
            priority_claims = [priority_claims]

        results = []
        for claim in priority_claims:
            doc_id = claim.get("document-id", {})
            if isinstance(doc_id, list):
                doc_id = doc_id[0] if doc_id else {}
            results.append(
                {
                    "country": doc_id.get("country", {}).get("$", ""),
                    "doc_number": doc_id.get("doc-number", {}).get("$", ""),
                    "date": doc_id.get("date", {}).get("$", ""),
                }
            )

        return results


def get_last_wednesday(reference_date: date | None = None) -> date:
    """Get the most recent Wednesday before or on the reference date."""
    ref = reference_date or date.today()
    days_since_wednesday = (ref.weekday() - 2) % 7
    return ref - timedelta(days=days_since_wednesday)
