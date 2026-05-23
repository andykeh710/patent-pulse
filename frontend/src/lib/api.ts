import type {
  ArtifactListResponse,
  CliffListResponse,
  ConvergenceItem,
  CreateRunRequest,
  EstimateRequest,
  EstimateResponse,
  ExpiryItem,
  ExpiryOpportunityItem,
  ExpiryParams,
  ExpirySummary,
  ExpirySummaryResponse,
  Freshness,
  OpportunityItem,
  OpportunityListParams,
  PaginatedResponse,
  PatentDetail,
  PatentListItem,
  PatentListParams,
  RunListResponse,
  RunMetadata,
  RunSummary,
  SearchParams,
  SimilarPatentsResponse,
  Stats,
  SupplierListParams,
  SupplierListResponse,
  SupplierMapCountry,
  CompanyProfile,
  SupplierSummary,
  Summary,
  TabCounts,
  Topic,
  ThemeStats,
  TrendListResponse,
  TrendResponse,
  TrendsSummary,
  WatchlistItemResponse,
  SemanticSearchResponse,
  LinkedInPostResponse,
  LinkedInDraftResponse,
  TrendDrilldownPatentsResponse,
  TrendDrilldownAssigneesResponse,
  TrendNarrativeResponse,
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

  getFreshness: () => apiFetch<Freshness>(`/api/v1/patents/freshness`),

  getExpirySummary: () => apiFetch<ExpirySummary>(`/api/v1/patents/expiry-summary`),

  getTrend: () => apiFetch<TrendResponse>(`/api/v1/patents/trend`),

  getPriorityWatch: (
    bucket: "expiring_soon" | "recent" | "all" = "expiring_soon",
    pageSize = 12
  ) =>
    apiFetch<PaginatedResponse<PatentListItem>>(
      `/api/v1/patents/priority-watch?bucket=${bucket}&page_size=${pageSize}`
    ),

  generateWhyNow: (id: string) =>
    apiFetch<{ status: string; headline: string; summary: string; signals: { type: string; explanation: string }[]; confidence: string; limitations: string[] }>(
      `/api/v1/patents/${id}/why-now`,
      { method: "POST" }
    ),

  generateOpportunityNarrative: (id: string) =>
    apiFetch<{ status: string; opportunity_type: string; plain_english_opportunity: string; possible_products: string[]; target_customers: string[]; implementation_difficulty: string; commercial_timing: string; risks: string[] }>(
      `/api/v1/patents/${id}/opportunity-narrative`,
      { method: "POST" }
    ),

  generateTrendSnapshot: (id: string) =>
    apiFetch<{ status: string; artifact_id: string; trend_score: number; components: Record<string, { sub_score: number; weight: number; contribution: number }> }>(
      `/api/v1/patents/${id}/trend-snapshot`,
      { method: "POST" }
    ),

  generateAssigneeIntelligence: (id: string) =>
    apiFetch<{ status: string; artifact_id: string; assignee_intelligence_score: number; components: Record<string, { sub_score: number; weight: number; contribution: number }> }>(
      `/api/v1/patents/${id}/assignee-intelligence`,
      { method: "POST" }
    ),

  generateLinkedInPost: (patentId: string, tone?: string) =>
    apiFetch<LinkedInPostResponse>(
      `/api/v1/content/generate-linkedin`,
      {
        method: "POST",
        body: JSON.stringify({ patent_id: patentId, tone: tone ?? null }),
      }
    ),
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

  /** Sprint 2B: grouped counts for Expiry Radar summary cards. */
  getSummary: () =>
    apiFetch<ExpirySummaryResponse>(`/api/v1/expiry/summary`),

  /** Sprint 2B: high-value expiry opportunity candidates. */
  getOpportunities: (minScore = 30, limit = 20) =>
    apiFetch<{ items: ExpiryOpportunityItem[]; total: number }>(
      `/api/v1/expiry/opportunities?min_score=${minScore}&limit=${limit}`
    ),
};

export const themesApi = {
  list: () => apiFetch<Topic[]>(`/api/v1/themes`),
  getPatents: (id: string, params: { page?: number; page_size?: number; min_score?: number } = {}) =>
    apiFetch<PaginatedResponse<PatentListItem>>(`/api/v1/themes/${id}/patents?${toQueryString(params)}`),
  getStats: (id: string) => apiFetch<ThemeStats>(`/api/v1/themes/${id}/stats`),
};

export const topicsApi = {
  ...themesApi,
  create: (data: {
    name: string;
    description?: string;
    cpc_prefixes?: string[];
    assignee_keywords?: string[];
    title_keywords?: string[];
    keywords?: string[];
    opportunity_tags?: string[];
    min_opportunity_score?: number;
  }) =>
    apiFetch<Topic>(`/api/v1/themes`, { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<{
    name: string;
    description: string;
    cpc_prefixes: string[];
    assignee_keywords: string[];
    title_keywords: string[];
    keywords: string[];
    opportunity_tags: string[];
    min_opportunity_score: number;
    is_active: boolean;
  }>) =>
    apiFetch<Topic>(`/api/v1/themes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<{ deleted: boolean }>(`/api/v1/themes/${id}`, { method: "DELETE" }),
};

export const semanticApi = {
  query: (query: string, limit = 20) =>
    apiFetch<SemanticSearchResponse>(
      `/api/v1/semantic/query?query=${encodeURIComponent(query)}&limit=${limit}`,
      { method: "POST" }
    ),

  similar: (patentId: string, limit = 10) =>
    apiFetch<SimilarPatentsResponse>(
      `/api/v1/semantic/similar/${patentId}?limit=${limit}`
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

export const aiRunsApi = {
  estimate: (body: EstimateRequest) =>
    apiFetch<EstimateResponse>(`/api/v1/ai-runs/estimate`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  create: (body: CreateRunRequest) =>
    apiFetch<RunSummary>(`/api/v1/ai-runs`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  list: (limit = 50, taskType?: string) => {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (taskType) qs.set("task_type", taskType);
    return apiFetch<RunListResponse>(`/api/v1/ai-runs?${qs.toString()}`);
  },
  get: (id: string) => apiFetch<RunSummary>(`/api/v1/ai-runs/${id}`),
  artifacts: (id: string, limit = 50, offset = 0) =>
    apiFetch<ArtifactListResponse>(`/api/v1/ai-runs/${id}/artifacts?limit=${limit}&offset=${offset}`),
  meta: () => apiFetch<RunMetadata>(`/api/v1/ai-runs/meta/options`),
};

export const opportunityApi = {
  list: (params: OpportunityListParams = {}) =>
    apiFetch<PaginatedResponse<OpportunityItem>>(
      `/api/v1/opportunity?${toQueryString(params)}`
    ),
  tabCounts: () => apiFetch<TabCounts>(`/api/v1/opportunity/tab-counts`),
};

export const watchlistApi = {
  list: (tag?: string) => {
    const params = tag ? `?tag=${encodeURIComponent(tag)}` : "";
    return apiFetch<WatchlistItemResponse[]>(`/api/v1/watchlist${params}`);
  },
  add: (patent_id: string, note?: string) =>
    apiFetch<WatchlistItemResponse>(`/api/v1/watchlist`, {
      method: "POST",
      body: JSON.stringify({ patent_id, note }),
    }),
  remove: (item_id: string) =>
    apiFetch<{ deleted: boolean }>(`/api/v1/watchlist/${item_id}`, {
      method: "DELETE",
    }),
  check: (patent_id: string) =>
    apiFetch<{ in_watchlist: boolean; watchlist_item_id: string | null }>(
      `/api/v1/watchlist/check/${patent_id}`
    ),
};

export const trendsApi = {
  summary: () => apiFetch<TrendsSummary>(`/api/v1/trends/summary`),
  hot: (surface?: string, limit = 20) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (surface) params.set("surface", surface);
    return apiFetch<TrendListResponse>(`/api/v1/trends/hot?${params}`);
  },
  growing: (surface?: string, limit = 20) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (surface) params.set("surface", surface);
    return apiFetch<TrendListResponse>(`/api/v1/trends/growing?${params}`);
  },
  convergence: (limit = 30) =>
    apiFetch<ConvergenceItem[]>(`/api/v1/trends/convergence?limit=${limit}`),
  cliffs: (windowMonths?: number, minPatents = 5, limit = 30) => {
    const params = new URLSearchParams({ min_patents: String(minPatents), limit: String(limit) });
    if (windowMonths) params.set("window_months", String(windowMonths));
    return apiFetch<CliffListResponse>(`/api/v1/trends/cliffs?${params}`);
  },

  // Sprint 4 — drilldown endpoints.
  getDrilldownPatents: (surface: string, key: string, page = 1, pageSize = 20) =>
    apiFetch<TrendDrilldownPatentsResponse>(
      `/api/v1/trends/${surface}/${key}/patents?page=${page}&page_size=${pageSize}`
    ),

  getDrilldownAssignees: (surface: string, key: string) =>
    apiFetch<TrendDrilldownAssigneesResponse>(
      `/api/v1/trends/${surface}/${key}/assignees`
    ),

  getNarrative: (surface: string, key: string) =>
    apiFetch<TrendNarrativeResponse | null>(
      `/api/v1/trends/${surface}/${key}/narrative`
    ),

  generateNarrative: (surface: string, key: string) =>
    apiFetch<TrendNarrativeResponse>(
      `/api/v1/trends/${surface}/${key}/narrative`,
      { method: "POST" }
    ),
};

export const suppliersApi = {
  summary: () => apiFetch<SupplierSummary>(`/api/v1/suppliers/summary`),

  list: (params: SupplierListParams = {}) =>
    apiFetch<SupplierListResponse>(
      `/api/v1/suppliers?${toQueryString(params)}`
    ),

  map: () => apiFetch<SupplierMapCountry[]>(`/api/v1/suppliers/map`),

  profile: (name: string) =>
    apiFetch<CompanyProfile>(`/api/v1/suppliers/profile/${encodeURIComponent(name)}`),
};

export const healthApi = {
  check: () => apiFetch<{ status: string; database: string }>("/health"),
};

export const contentApi = {
  getDraft: (patentId: string) =>
    apiFetch<LinkedInDraftResponse | null>(
      `/api/v1/content/drafts?patent_id=${patentId}`
    ),
};
