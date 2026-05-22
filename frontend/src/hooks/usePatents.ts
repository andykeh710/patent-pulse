import useSWR from "swr";
import { useRef } from "react";
import { patentsApi, searchApi } from "@/lib/api";
import type {
  ExpirySummary,
  PaginatedResponse,
  PatentDetail,
  PatentListItem,
  PatentListParams,
  SearchParams,
  Stats,
  Summary,
  TrendResponse,
} from "@/lib/types";

const MAX_POLL_FAILURES = 10;
const POLL_BASE_MS = 5000;
const POLL_MAX_MS = 60000;

export function usePatents(params: PatentListParams = {}) {
  const key = ["patents", JSON.stringify(params)];
  return useSWR<PaginatedResponse<PatentListItem>>(key, () =>
    patentsApi.list(params)
  );
}

export function usePatent(id: string | null) {
  return useSWR<PatentDetail>(id ? ["patent", id] : null, () =>
    patentsApi.get(id!)
  );
}

export function usePatentSummary(id: string | null) {
  const failCountRef = useRef(0);

  return useSWR<Summary | null>(
    id ? ["patent-summary", id] : null,
    () => patentsApi.getSummary(id!),
    {
      refreshInterval: (data) => {
        if (data !== null) {
          failCountRef.current = 0;
          return 0;
        }
        failCountRef.current += 1;
        if (failCountRef.current > MAX_POLL_FAILURES) return 0;
        const delay = Math.min(
          POLL_BASE_MS * Math.pow(2, failCountRef.current - 1),
          POLL_MAX_MS
        );
        return delay;
      },
      refreshWhenHidden: false,
    }
  );
}

export function usePatentStats() {
  return useSWR<Stats>(["patent-stats"], () => patentsApi.getStats());
}

export function usePatentSearch(params: SearchParams | null) {
  const key = params ? ["search", JSON.stringify(params)] : null;
  return useSWR<PaginatedResponse<PatentListItem>>(key, () =>
    searchApi.search(params!)
  );
}

export function useExpirySummary() {
  return useSWR<ExpirySummary>(["expiry-summary"], () => patentsApi.getExpirySummary());
}

export function usePatentTrend() {
  return useSWR<TrendResponse>(["patent-trend"], () => patentsApi.getTrend());
}

export function usePriorityWatch(
  bucket: "expiring_soon" | "recent" | "all" = "expiring_soon",
  pageSize = 12
) {
  return useSWR<PaginatedResponse<PatentListItem>>(
    ["priority-watch", bucket, pageSize],
    () => patentsApi.getPriorityWatch(bucket, pageSize)
  );
}
