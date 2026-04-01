import useSWR from "swr";
import { expiryApi } from "@/lib/api";
import type { ExpiryItem, ExpiryParams, PaginatedResponse } from "@/lib/types";

export function useExpiry(params: ExpiryParams = {}) {
  const key = ["expiry", JSON.stringify(params)];
  return useSWR<PaginatedResponse<ExpiryItem>>(key, () =>
    expiryApi.list(params)
  );
}
