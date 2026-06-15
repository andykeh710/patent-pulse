"use client";

import { ExpiryRadarCard, type ExpiryRadarCardProps } from "./ExpiryRadarCard";
import { EmptyState } from "@/components/ui/EmptyState";

interface ExpiryRadarSectionProps {
  title: string;
  description?: string;
  items: ExpiryRadarCardProps[];
  isLoading: boolean;
  emptyMessage: string;
  emptyDetail: string;
  /** Set of patent IDs the user has saved */
  savedIds?: Set<string>;
  /** Called when user toggles save on a card */
  onToggleSave?: (patentId: string) => void;
}

export function ExpiryRadarSection({
  title,
  description,
  items,
  isLoading,
  emptyMessage,
  emptyDetail,
  savedIds,
  onToggleSave,
}: ExpiryRadarSectionProps) {
  return (
    <div>
      <div className="mb-3">
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h2>
        {description && (
          <p className="text-sm text-[var(--text-muted)] mt-0.5">{description}</p>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)] p-4 animate-pulse"
            >
              <div className="h-4 bg-[var(--bg-glass)] rounded w-2/3 mb-2" />
              <div className="h-3 bg-[var(--bg-glass)] rounded w-1/3 mb-3" />
              <div className="flex gap-2">
                <div className="h-5 bg-[var(--bg-glass)] rounded w-20" />
                <div className="h-5 bg-[var(--bg-glass)] rounded w-16" />
              </div>
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon="calendar"
          title={emptyMessage}
          message={emptyDetail}
          detail="Expiry data is computed from filing metadata. New estimates appear as patents are ingested and assessed."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {items.map((item) => (
            <ExpiryRadarCard
              key={item.id}
              {...item}
              isSaved={savedIds?.has(item.id)}
              onToggleSave={onToggleSave}
            />
          ))}
        </div>
      )}
    </div>
  );
}
