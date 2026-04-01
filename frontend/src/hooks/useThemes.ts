import useSWR from "swr";
import { themesApi } from "@/lib/api";
import type { Theme, PaginatedResponse, PatentListItem } from "@/lib/types";

export function useThemes() {
  return useSWR<Theme[]>(["themes"], () => themesApi.list());
}

export function useThemePatents(id: string | null, page = 1, pageSize = 20) {
  return useSWR(
    id ? ["theme-patents", id, page] : null,
    () => themesApi.getPatents(id!, { page, page_size: pageSize })
  );
}
