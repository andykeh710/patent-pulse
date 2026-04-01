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
from typing import Any

import httpx

from app.config import settings
from app.core.exceptions import IngestionError, TransientIngestionError

logger = logging.getLogger(__name__)

EPO_AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
EPO_API_BASE = "https://ops.epo.org/3.2/rest-services"

TOKEN_REFRESH_BUFFER_SECONDS = 300


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

    def fetch_publication(self, publication_number: str) -> dict:
        """
        Fetch bibliographic data for a single publication.

        Args:
            publication_number: EP publication number (e.g., "EP1234567A1")

        Returns:
            Raw publication data dictionary
        """
        path = f"/published-data/publication/epodoc/{publication_number}/biblio"
        return self._request("GET", path)

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
                response = self._request("GET", path, params=params)
                publications = self._extract_publications(response)

                if not publications:
                    break

                for pub in publications:
                    yield pub

                if len(publications) < (range_end - range_begin + 1):
                    break

                range_begin = range_end + 1
                range_end = range_begin + 99

            except IngestionError:
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
                if doc:
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
