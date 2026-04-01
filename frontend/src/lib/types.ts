export interface Summary {
  what_it_is: string;
  problem_solved: string;
  how_it_works: string;
  commercial_significance: string;
  who_should_care: string[];
  novel_applications: NovelApplication[];
  confidence_note: string;
  source_spans: SourceSpan[];
}

export interface NovelApplication {
  application: string;
  label: "SPECULATIVE";
}

export interface SourceSpan {
  quote: string;
  field: "claims" | "description" | "abstract";
}

export interface ScoreBreakdown {
  cpc_relevance: number;
  assignee_notoriety: number;
  claim_breadth: number;
  family_breadth: number;
  semantic_novelty: number;
}

export interface PatentListItem {
  id: string;
  doc_id: string;
  publication_number: string;
  title: string | null;
  assignees: string[];
  cpc: string[];
  publication_date: string | null;
  grant_date: string | null;
  legal_status: string | null;
  interesting_score: number | null;
  summary_what_it_is: string | null;
  estimated_expiry_date: string | null;
}

export interface PatentDetail {
  id: string;
  doc_id: string;
  family_id: string | null;
  office: string;
  publication_number: string;
  application_number: string | null;
  kind_code: string | null;
  filing_date: string | null;
  priority_date: string | null;
  publication_date: string | null;
  grant_date: string | null;
  assignees: string[];
  inventors: string[];
  cpc: string[];
  ipc: string[];
  title: string | null;
  abstract: string | null;
  legal_status: string | null;
  maintenance_status: string | null;
  estimated_expiry_date: string | null;
  summary: Summary | null;
  novel_applications: string[];
  interesting_score: number | null;
  score_breakdown: ScoreBreakdown | null;
  family_members: string[];
  citations_backward: string[];
  summarized_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExpiryItem {
  id: string;
  doc_id: string;
  title: string | null;
  assignees: string[];
  estimated_expiry_date: string | null;
  days_until_expiry: number | null;
  legal_status: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Stats {
  total_patents: number;
  total_grants: number;
  total_applications: number;
  summarized_count: number;
  patents_this_week: number;
  top_cpc_sections: { section: string; count: number }[];
  top_assignees: { assignee: string; count: number }[];
}

export interface PatentListParams {
  office?: string;
  kind_code?: string;
  cpc_prefix?: string;
  assignee?: string;
  date_from?: string;
  date_to?: string;
  min_score?: number;
  sort_by?: "publication_date" | "interesting_score" | "created_at";
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface SearchParams {
  q: string;
  cpc?: string;
  assignee?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface ExpiryParams {
  days_ahead?: number;
  office?: string;
  page?: number;
  page_size?: number;
}

export interface ExpirySummary {
  within_30_days: number;
  within_90_days: number;
  within_365_days: number;
}

export interface TrendPoint {
  period: string;
  count: number;
}

export interface TrendResponse {
  points: TrendPoint[];
}

export interface Theme {
  id: string;
  name: string;
  description: string | null;
  cpc_prefixes: string[];
  assignee_keywords: string[];
  title_keywords: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ThemeStats {
  total_matches: number;
  avg_score: number;
  top_assignees: string[];
  recent_matches: number;
}

export interface SemanticSearchResult {
  patent: PatentListItem;
  similarity: number;
  distance: number;
}

export interface SemanticSearchResponse {
  results: SemanticSearchResult[];
  query: string;
  total: number;
}
