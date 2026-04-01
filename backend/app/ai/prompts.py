SYSTEM_PROMPT = """You are a patent intelligence analyst. Your role is to make \
patents understandable to business, product, and strategy professionals who \
are NOT lawyers or patent engineers. Be concrete, direct, and honest about \
uncertainty. Never invent technical details not present in the source text."""

SUMMARY_SCHEMA_DESCRIPTION = """
Respond with a JSON object matching this exact structure:
{
  "what_it_is": "1-2 sentences describing the invention in plain language",
  "problem_solved": "The specific technical or business problem this invention addresses",
  "how_it_works": "The mechanism - how the invention actually achieves its goal",
  "commercial_significance": "Why this matters commercially or strategically",
  "who_should_care": ["Role or industry 1", "Role or industry 2", "Role or industry 3"],
  "novel_applications": [
    {"application": "A potential downstream use of this technology", "label": "SPECULATIVE"}
  ],
  "confidence_note": "Brief note on certainty level given the source text quality",
  "source_spans": [
    {"quote": "exact quoted text from claims or description", "field": "claims|description|abstract"}
  ]
}

IMPORTANT RULES:
- novel_applications MUST all have label: "SPECULATIVE" - never present speculation as fact
- source_spans MUST be verbatim quotes from the provided text, not paraphrases
- If the abstract or claims are missing/unclear, note this explicitly in confidence_note
- Keep language accessible - avoid legal jargon like "comprising" or "wherein"
- Be specific about the mechanism, not just the goal
- who_should_care should list 3-5 specific roles or industries
"""

USER_PROMPT_TEMPLATE = """Analyze the following patent and produce a structured summary.

TITLE: {title}

ABSTRACT:
{abstract}

INDEPENDENT CLAIMS:
{claims_text}

DESCRIPTION EXCERPT (first 2000 chars):
{description_excerpt}

CPC CLASSIFICATIONS: {cpc_codes}

{schema_description}
"""

CLAIMS_EXTRACTION_PROMPT = """Extract only the independent claims from this claims text.
Independent claims are those that do NOT reference another claim number.
Return each independent claim on its own line, numbered.

Claims text:
{claims_text}
"""
