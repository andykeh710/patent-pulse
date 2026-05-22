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

// ---------------------------------------------------------------------------
// Phase 1 intelligence shapes
// ---------------------------------------------------------------------------

export type LegalStatusConfidence = "estimated" | "confirmed";
export type TimeHorizon = "now" | "near_term" | "long_term" | "unknown";

/** Output of the tag_patent_v1 prompt. Denormalized on PatentPublication.tags. */
export interface PatentTags {
  industries: string[];
  problem_solved: string;
  technology_method: string[];
  materials: string[];
  novel_application_categories: string[];
  time_horizon: TimeHorizon;
  risk_flags: string[];
  opportunity_tags: string[];
  trend_tags: string[];
}

/** Single component contribution inside the opportunity-score breakdown. */
export interface OpportunityComponent {
  sub_score: number;     // 0..1
  weight: number;        // 0..1
  contribution: number;  // 0..1  (sub_score * weight)
}

/** Canonical content_json shape for AIArtifact(opportunity_score). */
export interface OpportunityBreakdown {
  score: number;         // 0..100
  version: number;       // rules version
  weights: Record<string, number>;
  components: Record<string, OpportunityComponent>;
  computed_at: string;
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
  legal_status_confidence: LegalStatusConfidence;
  interesting_score: number | null;
  opportunity_score: number | null;
  tags: PatentTags | null;
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
  claims_text: string | null;
  legal_status: string | null;
  legal_status_confidence: LegalStatusConfidence;
  maintenance_status: string | null;
  estimated_expiry_date: string | null;
  summary: Summary | null;
  novel_applications: string[];
  interesting_score: number | null;
  score_breakdown: ScoreBreakdown | null;
  opportunity_score: number | null;
  opportunity_score_version: number | null;
  opportunity_breakdown: OpportunityBreakdown | null;
  tags: PatentTags | null;
  why_now_text: string | null;
  family_members: string[];
  citations_backward: string[];
  summarized_at: string | null;
  created_at: string;
  updated_at: string;
  presentation_rank_score: number | null;
  presentation_rank_reason: string | null;
  presentation_rank_confidence: string | null;
}

export interface ExpiryItem {
  id: string;
  doc_id: string;
  title: string | null;
  assignees: string[];
  estimated_expiry_date: string | null;
  days_until_expiry: number | null;
  legal_status: string | null;
  legal_status_confidence: string;
  opportunity_score: number | null;
  tags: PatentTags | null;
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

export interface Freshness {
  latest_patent_created_at: string | null;
  latest_patent_publication_date: string | null;
  latest_summarized_at: string | null;
  latest_trend_snapshot_at: string | null;
  latest_ai_run_at: string | null;
  total_patents: number;
  total_summarized: number;
  total_trend_snapshots: number;
}

export interface PatentListParams {
  office?: string;
  kind_code?: string;
  cpc_prefix?: string;
  assignee?: string;
  date_from?: string;
  date_to?: string;
  min_score?: number;
  max_score?: number;
  sort_by?: "publication_date" | "interesting_score" | "opportunity_score" | "created_at";
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
  industry?: string;
  time_horizon?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}

export interface ExpirySummary {
  within_5_years: number;
  within_10_years: number;
  within_20_years: number;
  total_with_expiry: number;
}

export interface TrendPoint {
  period: string;
  count: number;
}

export interface TrendResponse {
  points: TrendPoint[];
}

export interface Topic {
  id: string;
  name: string;
  description: string | null;
  cpc_prefixes: string[];
  assignee_keywords: string[];
  title_keywords: string[];
  keywords: string[] | null;
  opportunity_tags: string[] | null;
  min_opportunity_score: number | null;
  user_id: string | null;
  is_active: boolean;
  patent_count: number;
  created_at: string;
}

/** @deprecated Use Topic instead */
export type Theme = Topic;

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

export interface SimilarPatentsResponse {
  source_patent_id: string;
  results: SemanticSearchResult[];
  total: number;
}

// ---------------------------------------------------------------------------
// AI Runs (Phase 0 admin console)
// ---------------------------------------------------------------------------

export type AITaskType =
  | "summary"
  | "tags"
  | "opportunity_score"
  | "interesting_score"
  | "why_now"
  | "opportunity_narrative"
  | "trend_narrative"
  | "assignee_narrative"
  | "score_rerank";

export type AIRunMode = "dev_fixture" | "sample" | "cohort" | "full_batch";

export interface CohortFilter {
  patent_ids?: string[];
  cpc_prefix?: string | null;
  grant_year_from?: number | null;
  grant_year_to?: number | null;
  expiry_within_days?: number | null;
  has_summary?: boolean | null;
  has_abstract?: boolean | null;
  has_tags?: boolean | null;
  has_opportunity_score?: boolean | null;
  min_interesting_score?: number | null;
  max_interesting_score?: number | null;
  limit?: number | null;
}

export interface EstimateRequest {
  task_type: AITaskType;
  run_mode: AIRunMode;
  cohort: CohortFilter;
  tier?: "summary" | "tag" | "narrative" | "rerank";
}

export interface EstimateResponse {
  task_type: string;
  run_mode: string;
  cohort_size: number;
  cached_count: number;
  uncached_count: number;
  est_input_tokens: number;
  est_output_tokens: number;
  est_cost_usd: number;
  model: string;
  prompt_name: string;
  prompt_version: number;
  prompt_hash: string;
  expected_cache_hit_rate_7d: number;
  auto_approve_threshold_usd: number;
  full_batch_threshold_usd: number;
  requires_confirmation: boolean;
  requires_full_batch_phrase: boolean;
}

export interface CreateRunRequest extends EstimateRequest {
  confirmation_phrase?: string;
  enqueue?: boolean;
}

export interface RunSummary {
  id: string;
  task_type: string;
  run_mode: string;
  status: string;
  cohort_size: number;
  cached_count: number;
  uncached_count: number;
  est_cost_usd: number;
  actual_cost_usd: number;
  completed_count: number;
  failed_count: number;
  model: string;
  prompt_name: string | null;
  prompt_version: number | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ArtifactSummary {
  id: string;
  patent_publication_id: string | null;
  artifact_type: string;
  artifact_version: number;
  model: string;
  prompt_name: string;
  prompt_version: number;
  status: string;
  input_tokens: number;
  output_tokens: number;
  actual_cost_usd: number;
  content_json_preview: Record<string, unknown> | null;
  created_at: string;
}

export interface ArtifactListResponse {
  items: ArtifactSummary[];
  total: number;
}

export interface RunListResponse {
  items: RunSummary[];
  total: number;
}

export interface RunMetadata {
  task_types: string[];
  run_modes: string[];
  auto_approve_threshold_usd: number;
  full_batch_threshold_usd: number;
  default_user_id: string;
  llm_mode: string;
}

// ---------------------------------------------------------------------------
// Opportunity page (Phase 1)
// ---------------------------------------------------------------------------

export type OpportunityTab =
  | "top"
  | "expired"
  | "revival"
  | "cross_industry"
  | "startup"
  | "enterprise"
  | "sustainability"
  | "legal_review";

export type OpportunitySort =
  | "opportunity_score"
  | "expiring_soon"
  | "newly_published"
  | "interesting_score"
  | "lowest_legal_risk"
  | "strongest_cross_industry";

export interface OpportunityItem {
  id: string;
  doc_id: string;
  title: string | null;
  assignees: string[];
  cpc: string[];
  publication_date: string | null;
  grant_date: string | null;
  estimated_expiry_date: string | null;
  days_until_expiry: number | null;
  legal_status: string | null;
  legal_status_confidence: LegalStatusConfidence;
  interesting_score: number | null;
  opportunity_score: number | null;
  opportunity_score_version: number | null;
  opportunity_breakdown: OpportunityBreakdown | null;
  tags: PatentTags | null;
  summary_what_it_is: string | null;
}

export interface OpportunityListParams {
  tab?: OpportunityTab;
  industry?: string;
  time_horizon?: TimeHorizon;
  risk_flag?: string;
  opportunity_tag?: string;
  legal_confidence?: LegalStatusConfidence;
  cpc_prefix?: string;
  assignee_keyword?: string;
  expiry_within_days?: number;
  min_score?: number;
  max_score?: number;
  sort?: OpportunitySort;
  page?: number;
  page_size?: number;
}

export interface TabCounts {
  top: number;
  expired: number;
  revival: number;
  cross_industry: number;
  startup: number;
  enterprise: number;
  sustainability: number;
  legal_review: number;
}

/** Controlled vocabulary constants, kept in sync with backend/app/ai/tagger.py. */
export const OPPORTUNITY_TAG_VALUES = [
  "expired_opportunity",
  "ai_revival_candidate",
  "startup_opportunity",
  "enterprise_automation",
  "manufacturing_reuse",
  "sustainability_angle",
  "low_competition",
  "public_domain_candidate",
  "cross_industry_transfer",
] as const;

export const RISK_FLAG_VALUES = [
  "needs_legal_review",
  "active_family_risk",
  "unknown_legal_status",
  "crowded_space",
  "platform_technology",
  "regulatory_dependency",
  "experimental_only",
] as const;

export type OpportunityTagValue = (typeof OPPORTUNITY_TAG_VALUES)[number];
export type RiskFlagValue = (typeof RISK_FLAG_VALUES)[number];

// ---------------------------------------------------------------------------
// Trends (Phase A/B)
// ---------------------------------------------------------------------------

export interface TrendItem {
  surface: string;
  key: string;
  week_start: string;
  count_4w: number;
  count_12w: number;
  baseline_12mo: number;
  z_score: number;
  growth_pct: number;
  assignee_diversity: number;
  cpc_diversity: number;
  top_patent_ids: string[];
}

export interface TrendListResponse {
  items: TrendItem[];
  total: number;
}

export interface ConvergenceItem {
  cpc_a: string;
  cpc_b: string;
  joint_count: number;
  baseline_count: number;
  growth_ratio: number;
}

export interface CliffClusterItem {
  id: string;
  key_type: string;
  key_value: string;
  window_months: number;
  patent_count: number;
  representative_patent_ids: string[];
}

export interface CliffListResponse {
  items: CliffClusterItem[];
  total: number;
}

export interface WatchlistItemResponse {
  id: string;
  patent: PatentListItem;
  note: string | null;
  tags: string[];
  added_at: string;
}

export interface TrendsSummary {
  total_trend_rows: number;
  surfaces: Record<string, number>;
  convergence_signals: number;
  cliff_clusters: number;
  last_computed: string | null;
}

export interface SupplierSummary {
  total_suppliers: number;
  suppliers_with_country: number;
  suppliers_with_entity_type: number;
  total_supplier_patents: number;
  average_patents_per_supplier: number;
  high_opportunity_suppliers: number;
  countries: { country: string; count: number }[];
  entity_types: { entity_type: string; count: number }[];
}

export interface SupplierItem {
  name: string;
  country: string | null;
  entity_type: string | null;
  patent_count: number;
  active_patent_count: number;
  expiring_soon_count: number;
  technology_area_count: number;
  average_signal_score: number | null;
  supplier_score: number;
}

export interface SupplierListParams {
  country?: string;
  entity_type?: string;
  min_patent_count?: number;
  sort_by?: "supplier_score" | "patent_count" | "active_patent_count" | "average_signal_score";
  sort_order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface SupplierListResponse {
  items: SupplierItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SupplierMapCountry {
  country: string;
  supplier_count: number;
  patent_count: number;
  average_supplier_score: number;
  top_suppliers: { name: string; patent_count: number; supplier_score: number }[];
}

export interface CompanyProfile {
  name: string;
  country: string | null;
  entity_type: string | null;
  patent_count: number;
  active_patent_count: number;
  expiring_soon_count: number;
  technology_area_count: number;
  average_signal_score: number | null;
  supplier_score: number;
  top_cpc: { cpc: string; count: number }[];
  recent_patents: { id: string; doc_id: string; title: string | null; publication_date: string | null; opportunity_score: number | null }[];
}
