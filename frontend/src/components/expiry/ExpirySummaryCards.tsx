"use client";

interface SummaryData {
  total_with_expiry: number;
  by_status: Record<string, number>;
  with_family_risk: number;
  high_opportunity_count: number;
}

interface ExpirySummaryCardsProps {
  data: SummaryData | null;
  isLoading: boolean;
}

export function ExpirySummaryCards({ data, isLoading }: ExpirySummaryCardsProps) {
  const cards = [
    {
      label: "Total with Expiry",
      value: data?.total_with_expiry ?? null,
      color: "text-gray-900",
    },
    {
      label: "Expiring Soon",
      value: (data?.by_status?.expiring_soon || 0),
      color: "text-amber-600",
    },
    {
      label: "High Opportunity",
      value: data?.high_opportunity_count ?? null,
      color: "text-emerald-600",
    },
    {
      label: "Family Risk",
      value: data?.with_family_risk ?? null,
      color: "text-red-600",
    },
  ];

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {cards.map((card) => (
          <div
            key={card.label}
            className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse"
          >
            <div className="h-3 bg-gray-200 rounded w-20 mb-2" />
            <div className="h-6 bg-gray-200 rounded w-12" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-white rounded-lg border border-gray-200 p-4"
        >
          <p className="text-xs text-gray-500 uppercase tracking-wider">
            {card.label}
          </p>
          <p className={`text-2xl font-bold mt-1 ${card.color}`}>
            {card.value != null ? card.value.toLocaleString() : "—"}
          </p>
        </div>
      ))}
    </div>
  );
}
