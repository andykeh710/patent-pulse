"""
Phase 3 — Patent retrieval for the RAG chatbot.

Embeds the user's query via ``PatentEmbedder`` (OpenAI text-embedding-3-small),
then queries patent_publications via pgvector cosine similarity to find the
top-K most relevant patents.

Uses the HNSW index created in Phase 1 PR 1 (idx_patents_embedding_hnsw).
Sets ``hnsw.ef_search=100`` per session for higher recall at query time.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedder import PatentEmbedder
from app.config import settings

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────

DEFAULT_RETRIEVE_K: int = 8
MIN_SIMILARITY: float = 0.3  # lower than search UI; chat queries are shorter


def _get_retrieve_k() -> int:
    env_val = getattr(settings, "chat_retrieve_k", None)
    if env_val is not None:
        try:
            return int(env_val)
        except (TypeError, ValueError):
            pass
    return DEFAULT_RETRIEVE_K


# ── Public API ────────────────────────────────────────────────────────


async def retrieve_patents(
    query: str,
    session: AsyncSession,
    k: int | None = None,
) -> list[dict]:
    """Embed query and retrieve top-K patents by cosine similarity.

    Args:
        query: The user's chat message.
        session: Active SQLAlchemy async session.
        k: Number of patents to retrieve (default from ``CHAT_RETRIEVE_K`` env
           or 8).

    Returns:
        List of patent dicts with keys: doc_id, title, abstract_excerpt,
        assignees, publication_date. Sorted by similarity descending.
        Empty list if no patents match or the embedder fails.
    """
    limit = k if k is not None else _get_retrieve_k()

    # 1. Generate query embedding
    try:
        with PatentEmbedder() as embedder:
            query_embedding = embedder.generate_embedding(query)
    except Exception:
        logger.exception("Failed to embed chat query; returning empty results")
        return []

    if not query_embedding:
        return []

    # 2. Set hnsw ef_search for higher recall
    await session.execute(text("SET LOCAL hnsw.ef_search = 100"))

    # 3. Vector similarity search
    embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

    sql = text(
        """
        SELECT
            p.doc_id,
            p.title,
            p.abstract,
            p.assignees,
            p.publication_date,
            1 - (p.embedding <=> CAST(:emb AS vector)) AS similarity
        FROM patent_publications p
        WHERE p.embedding IS NOT NULL
          AND 1 - (p.embedding <=> CAST(:emb AS vector)) >= :min_sim
        ORDER BY p.embedding <=> CAST(:emb AS vector) ASC
        LIMIT :limit
        """
    )

    result = await session.execute(
        sql,
        {
            "emb": embedding_str,
            "min_sim": MIN_SIMILARITY,
            "limit": limit,
        },
    )
    rows = result.fetchall()

    # 4. Build result dicts
    patents = []
    for row in rows:
        doc_id = row[0]
        title = row[1] or "Untitled"
        abstract = row[2] or ""
        assignees = row[3] or []
        pub_date = row[4]
        similarity = float(row[5]) if row[5] is not None else 0.0

        # Truncate abstract to ~200 chars for context window economy
        abstract_excerpt = abstract[:200]
        if len(abstract) > 200:
            abstract_excerpt = abstract_excerpt.rsplit(" ", 1)[0] + "…"

        patents.append(
            {
                "doc_id": doc_id,
                "title": title,
                "abstract_excerpt": abstract_excerpt,
                "assignees": assignees[:3],  # max 3 assignees
                "publication_date": (
                    str(pub_date) if pub_date else "unknown"
                ),
                "similarity": round(similarity, 3),
            }
        )

    logger.info(
        "chat_retrieval: q='%s' → %d patents (k=%d)",
        query[:80],
        len(patents),
        limit,
    )
    return patents


# ── System prompt builder ─────────────────────────────────────────────


CHAT_SYSTEM_PROMPT = """You are an analyst helping the user understand patents.
Be concise, factual, and avoid speculation.

Here are the most relevant patents to the user's question:

{retrieved_context}

When referencing a patent, use the format [doc_id] (e.g. [USPTO:US12345678]).
The UI will turn these into clickable links.

You have access to tools to look up patents and compare companies.
Use them proactively when the user asks about:
  - Specific patents (use open_patent with the doc_id)
  - Topics not in the retrieved patents above (use search_patents)
  - Multiple companies or competitive analysis (use compare_companies)

CITATION RULES:
- Cite EVERY claim about a specific patent using [doc_id] format.
  Example: '[USPTO:US12345678] discusses solid-state battery electrolytes.'
- Only cite doc_ids that are in the retrieved patents above OR that you
  obtained via the open_patent / search_patents / compare_companies tools.
- DO NOT invent doc_ids. If you don't have a source, qualify with
  'reportedly', 'in general', or similar — but do not fabricate.
- Use only USPTO:, EPO:, or WIPO: prefixes.

If the retrieved patents don't answer the question, say so honestly.
Never fabricate patent data, dates, or assignee names."""


def build_system_prompt(patents: list[dict]) -> str:
    """Build the system prompt with retrieved patent context.

    Args:
        patents: List of patent dicts from ``retrieve_patents``.

    Returns:
        System prompt string with numbered patent entries.
    """
    if not patents:
        return CHAT_SYSTEM_PROMPT.format(
            retrieved_context=(
                "No patents matching the user's query were found in the database. "
                "Acknowledge this honestly and suggest the user try a broader query."
            )
        )

    entries = []
    for i, p in enumerate(patents, start=1):
        assignee_str = ", ".join(p["assignees"]) if p["assignees"] else "Unknown"
        entries.append(
            f"[{i}] {p['doc_id']} — {p['title']}\n"
            f"    Assignee: {assignee_str} | Published: {p['publication_date']}\n"
            f"    {p['abstract_excerpt']}"
        )

    context = "\n\n".join(entries)
    return CHAT_SYSTEM_PROMPT.format(retrieved_context=context)
