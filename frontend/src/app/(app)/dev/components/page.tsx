"use client";

import { Card } from "@/components/ui/Card";
import { StatTile } from "@/components/ui/StatTile";
import { BriefingItem } from "@/components/ui/BriefingItem";
import { Pill } from "@/components/ui/Pill";
import { Button } from "@/components/ui/Button";
import { LiveIndicator } from "@/components/ui/LiveIndicator";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";

export default function ComponentShowcase() {
  return (
    <div className="py-8 space-y-12 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold text-[var(--text-primary)] mb-2">
          Phase A — Component Showcase
        </h1>
        <p className="text-sm text-[var(--text-muted)]">
          All primitives rendered in the dark/premium theme.
        </p>
      </div>

      {/* Card variants */}
      <section>
        <SectionHeader title="Card" label="Surfaces" />
        <div className="grid grid-cols-3 gap-4">
          <Card>Glass (default)</Card>
          <Card variant="default">Default</Card>
          <Card variant="elevated">Elevated</Card>
          <Card interactive className="col-span-3">
            Interactive — hover me (scan sweep + elevation)
          </Card>
        </div>
      </section>

      {/* StatTile */}
      <section>
        <SectionHeader title="StatTile" label="Data display" />
        <div className="grid grid-cols-4 gap-4">
          <StatTile label="Index size" value={64231} subtext="USPTO · EPO · WIPO" />
          <StatTile label="New this week" value={1247} subtext="↑ 12% vs avg" accent="signal" />
          <StatTile label="Your follows" value={7} subtext="4 topics · 3 companies" />
          <StatTile label="Expiring 90d" value={47} subtext="In your topics" accent="warning" />
        </div>
      </section>

      {/* BriefingItem types */}
      <section>
        <SectionHeader
          title="BriefingItem"
          label="Feed items"
          meta="All 6 types with required fields (reason, source, freshness)"
        />
        <div className="space-y-3">
          <BriefingItem
            type="trend"
            label="Filing trend · momentum"
            title="G06T image processing surges 42%"
            subtext="Samsung, NVIDIA lead"
            reason="Shown because you follow NVIDIA and G06T"
            source="USPTO direct"
            freshness={{ updated_at: "2026-06-01T08:30:00Z", relative: "2h ago" }}
          />
          <BriefingItem
            type="notable"
            label="Notable patent"
            title="Bio-based succinic acid composition"
            subtext="BASF SE · US20260146129"
            reason="High opportunity score in your Biotech topic"
            source="USPTO direct"
            freshness={{ updated_at: "2026-06-01T07:15:00Z", relative: "3h ago" }}
            confidence={{ level: "medium", caveat: "AI-generated summary — verify" }}
          />
          <BriefingItem
            type="company"
            label="Company move"
            title="Apple Inc. expands into H10W semiconductor filings"
            reason="You follow Apple Inc."
            source="WIPO BigQuery"
            freshness={{ updated_at: "2026-06-01T06:00:00Z", relative: "4h ago" }}
          />
          <BriefingItem
            type="expiring"
            label="Expiring opportunity"
            title="47 high-value patents in your topics expire within 90 days"
            reason="Matches your Operator persona and Clean Energy topic"
            source="USPTO · computed expiry estimates"
            freshness={{ updated_at: "2026-05-31T22:00:00Z", relative: "12h ago" }}
            confidence={{ level: "low", caveat: "Verify with official registers" }}
          />
          <BriefingItem
            type="foryou"
            label="For you · early personalization"
            title="Personalized feed will appear here as you follow topics and companies"
            reason="Based on your Operator persona"
            source="Invention Index 8"
            freshness={{ updated_at: "2026-06-01T00:00:00Z", relative: "14h ago" }}
          />
          <BriefingItem
            type="news"
            label="News · V1.1"
            title="News-patent linking slot reserved for V1.1"
            reason="V1.1 feature — will link real news to relevant patents"
            source="Invention Index 8"
            freshness={{ updated_at: "2026-06-01T00:00:00Z", relative: "14h ago" }}
          />
        </div>
      </section>

      {/* Pills */}
      <section>
        <SectionHeader title="Pill" label="Chips & labels" />
        <div className="flex flex-wrap gap-2">
          {(["indigo", "violet", "cyan", "green", "amber", "red", "gray"] as const).map((tone) => (
            <Pill key={tone} tone={tone}>{tone}</Pill>
          ))}
          <Pill tone="indigo" variant="outline">outline</Pill>
          <Pill tone="green" mono>42,231</Pill>
        </div>
      </section>

      {/* Buttons */}
      <section>
        <SectionHeader title="Button" label="Actions" />
        <div className="flex flex-wrap gap-3">
          <Button variant="primary">Primary CTA</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="primary" disabled>Disabled</Button>
        </div>
      </section>

      {/* LiveIndicator */}
      <section>
        <SectionHeader title="LiveIndicator" label="Status" />
        <div className="flex gap-6">
          <LiveIndicator state="live" />
          <LiveIndicator state="scanning" />
          <LiveIndicator state="updated" label="Updated 2m ago" />
          <LiveIndicator state="idle" />
        </div>
      </section>

      {/* Badge */}
      <section>
        <SectionHeader title="Badge" label="Legacy — refreshed for dark theme" />
        <div className="flex gap-2">
          <Badge variant="default">Default</Badge>
          <Badge variant="success">Success</Badge>
          <Badge variant="warning">Warning</Badge>
          <Badge variant="danger">Danger</Badge>
          <Badge variant="speculative">Speculative</Badge>
        </div>
      </section>

      {/* Skeleton */}
      <section>
        <SectionHeader title="Skeleton" label="Loading states" />
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      </section>

      {/* EmptyState */}
      <section>
        <SectionHeader title="EmptyState" label="Zero states" />
        <EmptyState
          icon="search"
          title="No results found"
          message="Try adjusting your search or filters."
          actions={[{ label: "Clear filters", onClick: () => {} }]}
        />
      </section>
    </div>
  );
}
