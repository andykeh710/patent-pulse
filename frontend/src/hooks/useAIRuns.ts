import useSWR from "swr";

import { aiRunsApi } from "@/lib/api";

export function useRunMetadata() {
  return useSWR(["ai-runs", "meta"], () => aiRunsApi.meta(), {
    revalidateOnFocus: false,
  });
}

export function useRunHistory(limit = 50, taskType?: string) {
  return useSWR(["ai-runs", "list", limit, taskType], () =>
    aiRunsApi.list(limit, taskType)
  );
}

export function useRunArtifacts(runId: string | null, limit = 50, offset = 0) {
  return useSWR(
    runId ? ["ai-runs", "artifacts", runId, limit, offset] : null,
    () => aiRunsApi.artifacts(runId!, limit, offset),
    { revalidateOnFocus: false }
  );
}
