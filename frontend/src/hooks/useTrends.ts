import useSWR from "swr";
import { trendsApi } from "@/lib/api";
import type {
  TrendListResponse,
  TrendsSummary,
  ConvergenceItem,
  CliffListResponse,
} from "@/lib/types";

export function useTrendsSummary() {
  return useSWR<TrendsSummary>("trends-summary", () => trendsApi.summary());
}

export function useHotTrends(surface?: string, limit = 20) {
  return useSWR<TrendListResponse>(
    ["trends-hot", surface, limit],
    () => trendsApi.hot(surface, limit)
  );
}

export function useGrowingTrends(surface?: string, limit = 20) {
  return useSWR<TrendListResponse>(
    ["trends-growing", surface, limit],
    () => trendsApi.growing(surface, limit)
  );
}

export function useConvergence(limit = 30) {
  return useSWR<ConvergenceItem[]>(
    ["trends-convergence", limit],
    () => trendsApi.convergence(limit)
  );
}

export function useCliffs(windowMonths?: number, minPatents = 5, limit = 30) {
  return useSWR<CliffListResponse>(
    ["trends-cliffs", windowMonths, minPatents, limit],
    () => trendsApi.cliffs(windowMonths, minPatents, limit)
  );
}
