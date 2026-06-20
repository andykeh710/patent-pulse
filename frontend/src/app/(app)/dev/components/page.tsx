"use client";

import { EvidenceRail } from "@/components/ui/EvidenceRail";
import { ConfidenceMark } from "@/components/ui/ConfidenceMark";
import type { ConfidenceLevel } from "@/components/ui/ConfidenceMark";
import { Score } from "@/components/ui/Score";
import type { ScoreKind, ScoreTier } from "@/components/ui/Score";
import { ProvenanceLine } from "@/components/ui/ProvenanceLine";
import { FreshnessChip } from "@/components/ui/FreshnessChip";
import type { FreshnessSource } from "@/components/ui/FreshnessChip";
import { DisclosureWarning } from "@/components/ui/DisclosureWarning";

export default function PrimitivesShowcase() {
  const confidenceLevels: ConfidenceLevel[] = [
    "confirmed",
    "high",
    "medium",
    "estimated",
    "low",
  ];

  const freshnessSources: FreshnessSource[] = [
    {
      label: "Patent Ingestion",
      status: "up",
      lastRun: "2h ago",
      newRecords: 142,
    },
    {
      label: "AI Summaries",
      status: "up",
      detail: "48,231 / 64,231 summarized",
    },
    {
      label: "Trends",
      status: "up",
      lastRun: "6h ago",
    },
    {
      label: "Source Lag",
      status: "stale",
      detail:
        "Latest patent publication: Jun 14 (8d ago). USPTO publishes Tue/Thu.",
    },
  ];

  const degradedSources: FreshnessSource[] = [
    {
      label: "Patent Ingestion",
      status: "down",
      lastRun: "3d ago",
      detail: "USPTO data APIs are unreachable",
    },
    {
      label: "AI Summaries",
      status: "stale",
      detail: "48,231 / 64,231 summarized — no new data to summarize",
    },
  ];

  return (
    <div className="py-8 space-y-16 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text)] mb-2">
          S0 — Design Primitives
        </h1>
        <p className="text-sm text-[var(--text-muted)]">
          &quot;The Bench&quot; — instrument-grade, evidence-first primitives.
          All rendered in the new token system.
        </p>
      </div>

      {/* ── EvidenceRail ── */}
      <section>
        <h2 className="text-lg font-semibold text-[var(--text)] mb-1">
          EvidenceRail
        </h2>
        <p className="text-xs text-[var(--text-muted)] mb-4">
          2px accent spine + provenance line in signature warm-neutral.
        </p>
        <div className="space-y-4">
          <EvidenceRail
            source="USPTO"
            docId="US12345678"
            confidence="high"
            verifyUrl="https://patents.google.com"
          >
            <h3 className="font-semibold text-[var(--text)] mb-1">
              Biodegradable implant with controlled drug release
            </h3>
            <p className="text-sm text-[var(--text-2)]">
              Medtronic · GRANTED · Expired (est.)
            </p>
            <p className="text-xs text-[var(--text-muted)] mt-2">
              A biodegradable polymer matrix that releases therapeutic agents at a controlled rate...
            </p>
          </EvidenceRail>

          <EvidenceRail
            source="EPO"
            docId="EP4025681"
            confidence="medium"
          >
            <h3 className="font-semibold text-[var(--text)] mb-1">
              Solid-state battery electrolyte composition
            </h3>
            <p className="text-sm text-[var(--text-2)]">
              Samsung SDI · PUBLISHED · Expiring soon
            </p>
          </EvidenceRail>

          <EvidenceRail
            source="WIPO"
            docId="WO2024012345"
            confidence="estimated"
          >
            <h3 className="font-semibold text-[var(--text)] mb-1">
              CRISPR delivery vector for in vivo gene therapy
            </h3>
            <p className="text-sm text-[var(--text-2)]">
              Editas Medicine · PUBLISHED
            </p>
          </EvidenceRail>
        </div>
      </section>

      {/* ── ConfidenceMark ── */}
      <section>
        <h2 className="text-lg font-semibold text-[var(--text)] mb-1">
          ConfidenceMark
        </h2>
        <p className="text-xs text-[var(--text-muted)] mb-4">
          Texture grammar: fill / solid ring / dashed ring / dotted ring.
          Colorblind-safe — redundant encoding (shape + label).
        </p>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {confidenceLevels.map((level) => (
            <div
              key={level}
              className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4 space-y-2"
            >
              <ConfidenceMark level={level} size="md" />
              <ConfidenceMark level={level} size="sm" />
              <ConfidenceMark level={level} size="dot" />
            </div>
          ))}
        </div>
      </section>

      {/* ── Score ── */}
      <section>
        <h2 className="text-lg font-semibold text-[var(--text)] mb-1">
          Score
        </h2>
        <p className="text-xs text-[var(--text-muted)] mb-4">
          Unified score display — integer only, tier dot, never two decimals.
          Kills the three-format inconsistency across pages.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {(
            [
              [82, "opportunity", "strong"],
              [57, "opportunity", "medium"],
              [22, "opportunity", "weak"],
              [0.75, "interesting", "strong"],
              [0.42, "interesting", "medium"],
              [0.11, "interesting", "weak"],
              [91, "composite", "strong"],
              [null, "opportunity", "weak"],
            ] as [number | null, ScoreKind, ScoreTier][]
          ).map(([value, kind, tier], i) => (
            <div
              key={i}
              className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4 space-y-2"
            >
              <Score value={value} kind={kind} tier={tier} size="md" />
              <Score value={value} kind={kind} tier={tier} size="sm" />
              <Score value={value} kind={kind} showLabel={false} />
            </div>
          ))}
        </div>
      </section>

      {/* ── ProvenanceLine ── */}
      <section>
        <h2 className="text-lg font-semibold text-[var(--text)] mb-1">
          ProvenanceLine
        </h2>
        <p className="text-xs text-[var(--text-muted)] mb-4">
          Source · doc_id · confidence · Verify at source ↗. Signature
          warm-neutral color. Geist Mono.
        </p>
        <div className="space-y-3">
          <ProvenanceLine
            source="USPTO"
            docId="US12345678"
            confidence="high"
            verifyUrl="https://patents.google.com"
          />
          <ProvenanceLine
            source="EPO"
            docId="EP4025681"
            confidence="medium"
          />
          <ProvenanceLine
            source="WIPO"
            docId="WO2024012345"
            confidence="estimated"
          />
        </div>
      </section>

      {/* ── FreshnessChip ── */}
      <section>
        <h2 className="text-lg font-semibold text-[var(--text)] mb-1">
          FreshnessChip
        </h2>
        <p className="text-xs text-[var(--text-muted)] mb-4">
          Always-on freshness indicator. States: fresh (green dot), stale
          (amber dot), degraded (red dot). Click opens popover.
        </p>
        <div className="space-y-4">
          <div>
            <p className="text-[11px] text-[var(--text-muted)] mb-1">
              Fresh — normal state
            </p>
            <FreshnessChip
              state="fresh"
              label="Updated 2h ago · 142 new"
              sources={freshnessSources}
            />
          </div>
          <div>
            <p className="text-[11px] text-[var(--text-muted)] mb-1">
              Stale — data &gt; 7d old
            </p>
            <FreshnessChip
              state="stale"
              label="Updated 8d ago"
              sources={freshnessSources}
            />
          </div>
          <div>
            <p className="text-[11px] text-[var(--text-muted)] mb-1">
              Degraded — source failure
            </p>
            <FreshnessChip
              state="degraded"
              label="Sources unavailable"
              sources={degradedSources}
            />
          </div>
          <div>
            <p className="text-[11px] text-[var(--text-muted)] mb-1">
              Simple — no popover
            </p>
            <FreshnessChip state="fresh" label="Updated 2h ago" simple />
          </div>
        </div>
      </section>

      {/* ── DisclosureWarning ── */}
      <section>
        <h2 className="text-lg font-semibold text-[var(--text)] mb-1">
          DisclosureWarning
        </h2>
        <p className="text-xs text-[var(--text-muted)] mb-4">
          V4-ready. Warns users before publishing confidential information.
        </p>
        <DisclosureWarning action="publish this insight" />
        <div className="mt-3">
          <DisclosureWarning action="share this comment" />
        </div>
      </section>
    </div>
  );
}
