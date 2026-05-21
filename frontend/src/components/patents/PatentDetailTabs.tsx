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
    <div className="border-b border-gray-200 mb-6">
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
                  ? "border-primary-500 text-primary-700"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-800")
              }
            >
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span
                  className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
                    active
                      ? "bg-primary-100 text-primary-700"
                      : "bg-gray-100 text-gray-500"
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
