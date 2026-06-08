---
title: "The 8 signals we track and why they matter"
subtitle: "Behind the name 'Invention Index 8' is a methodology"
excerpt: "We track eight independent signals per patent, per day, to surface what matters before the news catches up. Here's how each signal works."
author_name: "Invention Index 8"
author_role: "Research Team"
tags: ["product", "methodology", "signals"]
related_patent_doc_ids: []
related_theme_slugs: ["ai-ml", "semiconductor"]
related_company_names: []
status: published
---

# The 8 signals we track and why they matter

The number 8 in our name isn't arbitrary. It's the eight independent signal types we compute for every patent in our database, refreshed daily. Each signal answers a different question about a patent's trajectory.

Here's the full breakdown.

## 1. Filing Trend

**Question**: Is activity in this CPC area accelerating?

We count new filings per CPC code per week and compare against a rolling 12-week baseline. When a company triples its filing rate in an area they've barely touched before, that's a signal worth investigating.

Trend spikes often precede product announcements by 12-18 months. Samsung filed heavily in solid-state battery patents in 2018 — three years before publicly discussing their solid-state roadmap.

## 2. Expiry Window

**Question**: How soon does this patent expire, and what does that unlock?

Patent term is 20 years from earliest filing. When a patent expires, the claimed invention enters the public domain. We flag patents within 5 years of expiry, weighted by citation count (more cited = more valuable when freed).

Expiring patents create "free real estate" for competitors. The 2024-2028 window is particularly interesting: many foundational smartphone patents from the iPhone era start expiring.

## 3. Citation Velocity

**Question**: How quickly are other patents citing this one?

Raw citation count matters, but velocity matters more. A patent that receives 15 citations in its first year is more impactful than one that received 30 over 15 years. We compute a time-weighted citation score that rewards recency.

## 4. Assignee Intelligence

**Question**: Based on this company's filing patterns, how strategic is this patent?

We analyze the assignee's full filing history to determine whether this patent fits their existing portfolio or represents a new direction. A patent from Apple about "a method for manufacturing semiconductors" raises a different kind of flag than Apple's 50th iPhone antenna optimization.

## 5. Claim Breadth

**Question**: How broad or narrow is the legal coverage?

Independent claims define the invention's protected scope. Broad claims (fewer elements, more abstract language) cover more territory. Narrow claims (many elements, specific measurements) are easier to design around. We assign a breadth score by parsing claim structure.

## 6. Semantic Novelty

**Question**: How different is this from everything else?

We embed the patent's title + abstract + claims into vector space and measure cosine distance from the nearest 100 neighbors. High semantic novelty means the patent describes something genuinely new — not just another incremental improvement.

## 7. Opportunity Score

**Question**: If this patent expires, how attractive is the white space?

Composite of expiry urgency, citation count, claim breadth, and market size of the CPC area. Our highest-scoring expiring patents often map to billion-dollar markets.

## 8. Why Now (LLM-generated narrative)

**Question**: In plain English, why does this patent matter right now?

Our Sonnet-based pipeline reads all seven signals above and generates a short narrative: what changed, who should care, and the practical implications. It's not investment advice — it's research intelligence.

## Why eight?

Because one signal is noise. Three signals is a hunch. Eight signals, refreshed daily, is a pattern.

We built Invention Index 8 to answer one question: "What should I pay attention to in the patent landscape right now?" The eight signals are our answer.
