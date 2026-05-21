"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { usePatents } from "@/hooks/usePatents";
import { PatentCard } from "@/components/patents/PatentCard";
import { PatentCardSkeleton } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import type { PatentListParams } from "@/lib/types";

export default function PatentsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-gray-400">Loading...</div>}>
      <PatentsContent />
    </Suspense>
  );
}

function PatentsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [params, setParams] = useState<PatentListParams>({
    sort_by: (searchParams.get("sort_by") as PatentListParams["sort_by"]) || "publication_date",
    sort_order: (searchParams.get("sort_order") as PatentListParams["sort_order"]) || "desc",
    page: searchParams.get("page") ? Number(searchParams.get("page")) : 1,
    page_size: 20,
  });

  useEffect(() => {
    const sp = new URLSearchParams();
    if (params.sort_by !== "publication_date") sp.set("sort_by", params.sort_by!);
    if (params.sort_order !== "desc") sp.set("sort_order", params.sort_order!);
    if ((params.page ?? 1) > 1) sp.set("page", String(params.page));
    const qs = sp.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [params, pathname, router]);

  const { data, isLoading, error, mutate } = usePatents(params);

  const handleSortChange = (sortBy: string) => {
    setParams((prev) => ({
      ...prev,
      sort_by: sortBy as PatentListParams["sort_by"],
      page: 1,
    }));
  };

  const handlePageChange = (page: number) => {
    setParams((prev) => ({ ...prev, page }));
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Patents</h1>
          <p className="text-gray-600 mt-1">
            {data?.total ? `${data.total} patents` : "Browse all patents"}
          </p>
        </div>

        <div className="flex items-center gap-4">
          <select
            value={params.sort_by}
            onChange={(e) => handleSortChange(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="publication_date">Publication Date</option>
            <option value="interesting_score">Interest Score</option>
            <option value="opportunity_score">Opportunity Score</option>
            <option value="created_at">Recently Added</option>
          </select>
        </div>
      </div>

      {error ? (
        <ErrorState message="Failed to load patents." onRetry={() => mutate()} />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(9)].map((_, i) => (
            <PatentCardSkeleton key={i} />
          ))}
        </div>
      ) : data?.items.length === 0 ? (
        <EmptyState
          icon="patent"
          title="No patents found"
          message="Try adjusting your sort or check back after the next ingestion run."
        />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {data?.items.map((patent) => (
              <PatentCard key={patent.id} patent={patent} />
            ))}
          </div>

          {data && data.pages > 1 && (
            <div className="flex justify-center gap-2">
              <button
                onClick={() => handlePageChange(params.page! - 1)}
                disabled={params.page === 1}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-sm text-gray-600">
                Page {params.page} of {data.pages}
              </span>
              <button
                onClick={() => handlePageChange(params.page! + 1)}
                disabled={params.page === data.pages}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
