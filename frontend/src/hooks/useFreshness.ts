import useSWR from "swr";
import { patentsApi } from "@/lib/api";

export function useFreshness() {
  return useSWR("freshness", () => patentsApi.getFreshness(), {
    revalidateOnFocus: false,
    dedupingInterval: 60_000,
  });
}
