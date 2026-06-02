"use client";

interface Tab {
  id: string;
  label: string;
  count?: number;
}

interface PatentDetailTabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export function PatentDetailTabs({
  tabs,
  activeTab,
  onTabChange,
}: PatentDetailTabsProps) {
  return (
    <div className="border-b border-[var(--border-subtle)] mb-6">
      <nav className="flex gap-1 overflow-x-auto" aria-label="Patent detail tabs">
        {tabs.map((tab) => {
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onTabChange(tab.id)}
              className={
                "border-b-2 px-4 py-2.5 text-sm font-medium transition-colors whitespace-nowrap " +
                (active
                  ? "border-[var(--accent)] text-[var(--accent)]"
                  : "border-transparent text-[var(--text-muted)] hover:border-[var(--border-default)] hover:text-[var(--text-primary)]")
              }
            >
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span
                  className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
                    active
                      ? "bg-[var(--accent-muted)] text-[var(--accent)]"
                      : "bg-[var(--bg-elevated)] text-[var(--text-muted)]"
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
