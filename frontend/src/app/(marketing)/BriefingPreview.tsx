"use client";

export function BriefingPreview() {
  const items = [
    {
      docId: "USPTO:20260144033",
      score: 89,
      tier: "strong",
      confidence: "high",
    },
    {
      docId: "USPTO:20260144068",
      score: 86,
      tier: "strong",
      confidence: "high",
      selfCite: true,
    },
    {
      docId: "USPTO:20260144041",
      score: 82,
      tier: "strong",
      confidence: "medium",
    },
    {
      docId: "USPTO:20260144022",
      score: 78,
      tier: "medium",
      confidence: "high",
    },
    {
      docId: "USPTO:20260144055",
      score: 75,
      tier: "medium",
      confidence: "medium",
    },
  ];

  const tierColor = (t: string) =>
    t === "strong"
      ? "bg-green-100 text-green-800"
      : "bg-amber-100 text-amber-800";

  return (
    <div className="w-[340px] bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-primary-600 text-white px-5 py-3">
        <p className="text-xs font-semibold uppercase tracking-wider opacity-90">
          Your weekly briefing
        </p>
        <p className="text-sm font-medium mt-0.5">G06F · Computing</p>
      </div>

      {/* Items */}
      <div className="divide-y divide-gray-100">
        {items.map((item, i) => (
          <div
            key={item.docId}
            className={`px-5 py-3 ${i >= 2 ? "opacity-40" : ""}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-mono text-gray-500">
                {item.docId}
              </span>
              <span className="text-xs font-bold text-primary-700">
                Score {item.score}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${tierColor(
                  item.tier
                )}`}
              >
                {item.tier}
              </span>
              <span className="text-[10px] text-gray-400">
                confidence: {item.confidence}
              </span>
              {item.selfCite && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-yellow-100 text-yellow-800 border border-yellow-300">
                  ⚠ self-citation risk
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 bg-gray-50 border-t border-gray-100 text-right">
        <span className="text-xs text-primary-600 font-medium">
          {items.length - 2} more · view all →
        </span>
      </div>
    </div>
  );
}
