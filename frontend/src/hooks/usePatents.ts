import useSWR from "swr";
import { patentsApi, searchApi } from "@/lib/api";
import type {
  PaginatedResponse,
  PatentDetail,
  PatentListItem,
  PatentListParams,
  SearchParams,
  Stats,
  Summary,
} from "@/lib/types";

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
  return useSWR<Summary | null>(
    id ? ["patent-summary", id] : null,
    () => patentsApi.getSummary(id!),
    {
      refreshInterval: (data) => {
        if (data === null) return 5000;
        return 0;
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
