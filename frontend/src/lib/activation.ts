/** Activation state + setup nudges — Sprint 7. */

export interface ActivationState {
  user_id: string;
  has_opened_today: boolean;
  saved_patent_count: number;
  saved_search_count: number;
  followed_company_count: number;
  patent_detail_views: number;
  feedback_count: number;
  activated: boolean;
  strongly_activated: boolean;
  missing_steps: string[];
}

/** Fetch activation state from GET /api/v1/activation-state */
export async function fetchActivationState(): Promise<ActivationState | null> {
  try {
    const r = await fetch("/api/v1/activation-state", { credentials: "include" });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

/** Submit feedback via POST /api/v1/feedback */
export async function submitFeedback(params: {
  route: string;
  surface: string;
  rating: string;
  message?: string;
  object_type?: string;
  object_id?: string;
}): Promise<void> {
  await fetch("/api/v1/feedback", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  // Silent on failure — feedback must not block UX
}
