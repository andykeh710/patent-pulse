import useSWR, { mutate } from "swr";
import { watchlistApi } from "@/lib/api";
import type { WatchlistItemResponse } from "@/lib/types";

export function useWatchlist(tag?: string) {
  return useSWR<WatchlistItemResponse[]>(
    ["watchlist", tag],
    () => watchlistApi.list(tag)
  );
}

export function useWatchlistCheck(patentId: string | null) {
  return useSWR(
    patentId ? ["watchlist-check", patentId] : null,
    () => watchlistApi.check(patentId!)
  );
}

export async function addToWatchlist(patentId: string, note?: string) {
  const result = await watchlistApi.add(patentId, note);
  mutate((key: unknown) => Array.isArray(key) && key[0] === "watchlist");
  mutate(["watchlist-check", patentId]);
  return result;
}

export async function removeFromWatchlist(itemId: string, patentId: string) {
  await watchlistApi.remove(itemId);
  mutate((key: unknown) => Array.isArray(key) && key[0] === "watchlist");
  mutate(["watchlist-check", patentId]);
}
