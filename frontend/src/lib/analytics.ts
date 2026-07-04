/**
 * Lightweight analytics — Sprint 7.
 *
 * Logs product events to console.debug for dev visibility.
 * Wire to POST /api/v1/analytics/event or a third-party
 * endpoint when ready.  Non-blocking — failures are silent.
 */

interface AnalyticsEvent {
  event: string;
  screen?: string;
  user_id?: string;
  patent_id?: string;
  search_id?: string;
  filter?: string;
  sort?: string;
  action?: string;
  [key: string]: unknown;
}

export function trackEvent(event: string, payload?: Partial<AnalyticsEvent>) {
  const data: AnalyticsEvent = {
    event,
    ts: new Date().toISOString(),
    ...payload,
  };
  // Dev: log to console. Production: POST to analytics endpoint.
  console.debug("[analytics]", data);
  // Future:
  // fetch("/api/v1/analytics/event", {
  //   method: "POST",
  //   credentials: "include",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify(data),
  // }).catch(() => {});
}
