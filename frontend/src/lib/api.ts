import type {
  ExpiryItem,
  ExpiryParams,
  ExpirySummary,
  PaginatedResponse,
  PatentDetail,
  PatentListItem,
  PatentListParams,
  SearchParams,
  Stats,
  Summary,
  Theme,
  ThemeStats,
  TrendResponse,
  SemanticSearchResponse,
} from "./types";

const API_BASE = "";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new ApiError(res.status, error.detail || "Unknown error");
  }

  return res.json() as Promise<T>;
}

function toQueryString(params: Record<string, unknown> | object): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  }
  return searchParams.toString();
}

export const patentsApi = {
  list: (params: PatentListParams = {}) =>
    apiFetch<PaginatedResponse<PatentListItem>>(
      `/api/v1/patents?${toQueryString(params)}`
    ),

  get: (id: string) => apiFetch<PatentDetail>(`/api/v1/patents/${id}`),

  getSummary: (id: string) =>
    apiFetch<Summary | null>(`/api/v1/patents/${id}/summary`),

  getStats: () => apiFetch<Stats>(`/api/v1/patents/stats`),

  getExpirySummary: () => apiFetch<ExpirySummary>(`/api/v1/patents/expiry-summary`),

  getTrend: () => apiFetch<TrendResponse>(`/api/v1/patents/trend`),
};

export const searchApi = {
  search: (params: SearchParams) =>
    apiFetch<PaginatedResponse<PatentListItem>>(
      `/api/v1/search?${toQueryString(params)}`
    ),
};

export const expiryApi = {
  list: (params: ExpiryParams = {}) =>
    apiFetch<PaginatedResponse<ExpiryItem>>(
      `/api/v1/expiry?${toQueryString(params)}`
    ),
};

export const themesApi = {
  list: () => apiFetch<Theme[]>(`/api/v1/themes`),
  getPatents: (id: string, params: { page?: number; page_size?: number; min_score?: number } = {}) =>
    apiFetch<PaginatedResponse<PatentListItem>>(`/api/v1/themes/${id}/patents?${toQueryString(params)}`),
  getStats: (id: string) => apiFetch<ThemeStats>(`/api/v1/themes/${id}/stats`),
};

export const semanticApi = {
  query: (query: string, limit = 20) =>
    apiFetch<SemanticSearchResponse>(
      `/api/v1/semantic/query?query=${encodeURIComponent(query)}&limit=${limit}`,
      { method: "POST" }
    ),
};

export const adminApi = {
  triggerSummarize: (limit: number) =>
    apiFetch<{ task_id: string; status: string }>(`/api/v1/admin/trigger-summarize?limit=${limit}`, { method: "POST" }),
  triggerExpBackfill: () =>
    apiFetch<{ task_id: string; status: string }>(`/api/v1/admin/trigger-expiry-backfill`, { method: "POST" }),
  seedThemes: () =>
    apiFetch<{ created: number; skipped: number }>(`/api/v1/admin/seed-themes`, { method: "POST" }),
  triggerMatchThemes: () =>
    apiFetch<{ task_id: string; status: string }>(`/api/v1/admin/trigger-match-themes`, { method: "POST" }),
};

export const healthApi = {
  check: () => apiFetch<{ status: string; database: string }>("/health"),
};
