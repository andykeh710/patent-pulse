import useSWR from "swr";

import { opportunityApi } from "@/lib/api";
import type { OpportunityListParams } from "@/lib/types";

/** List patents ranked by opportunity_score with tabs/filters/sort. */
export function useOpportunityList(params: OpportunityListParams = {}) {
  // Stable cache key: sort the params alphabetically before serializing.
  const key = [
    "opportunity",
    "list",
    JSON.stringify(sortKeys(params as Record<string, unknown>)),
  ];
  return useSWR(key, () => opportunityApi.list(params), {
    keepPreviousData: true,
  });
}

/** Tab badges (counts per tab). */
export function useOpportunityTabCounts() {
  return useSWR(["opportunity", "tab-counts"], () => opportunityApi.tabCounts(), {
    revalidateOnFocus: false,
  });
}

function sortKeys<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(obj)
      .filter(([, v]) => v !== undefined && v !== null && v !== "")
      .sort(([a], [b]) => a.localeCompare(b))
  );
}
