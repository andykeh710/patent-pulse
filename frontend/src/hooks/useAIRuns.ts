import useSWR from "swr";

import { aiRunsApi } from "@/lib/api";
import type {
  ArtifactListResponse,
  RunListResponse,
  RunMetadata,
} from "@/lib/types";

export function useRunMetadata() {
  return useSWR<RunMetadata>(["ai-runs", "meta"], () => aiRunsApi.meta(), {
    revalidateOnFocus: false,
  });
}

export function useRunHistory(limit = 50, taskType?: string) {
  return useSWR<RunListResponse>(["ai-runs", "list", limit, taskType], () =>
    aiRunsApi.list(limit, taskType)
  );
}

export function useRunArtifacts(runId: string | null, limit = 50, offset = 0) {
  return useSWR<ArtifactListResponse>(
    runId ? ["ai-runs", "artifacts", runId, limit, offset] : null,
    () => aiRunsApi.artifacts(runId!, limit, offset),
    { revalidateOnFocus: false }
  );
}
