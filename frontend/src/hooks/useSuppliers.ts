import useSWR from "swr";
import { suppliersApi } from "@/lib/api";
import type { SupplierListParams, SupplierListResponse, SupplierMapCountry, SupplierSummary } from "@/lib/types";

export function useSupplierSummary() {
  return useSWR<SupplierSummary>(["supplier-summary"], () => suppliersApi.summary());
}

export function useSuppliers(params: SupplierListParams = {}) {
  return useSWR<SupplierListResponse>(["suppliers", JSON.stringify(params)], () => suppliersApi.list(params));
}

export function useSupplierMap() {
  return useSWR<SupplierMapCountry[]>(["supplier-map"], () => suppliersApi.map());
}
