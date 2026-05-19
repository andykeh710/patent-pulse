"use client";

import { useState } from "react";

import { useRunArtifacts, useRunHistory, useRunMetadata } from "@/hooks/useAIRuns";
import { aiRunsApi } from "@/lib/api";
import type {
  AIRunMode,
  AITaskType,
  ArtifactSummary,
  CohortFilter,
  EstimateResponse,
  RunSummary,
} from "@/lib/types";
import { formatDate } from "@/lib/utils";

const FULL_BATCH_PHRASE = "RUN FULL BATCH";

const TASK_TYPES: { value: AITaskType; label: string; supported: boolean }[] = [
  { value: "summary", label: "Summary (Sonnet)", supported: true },
  { value: "tags", label: "Tags (Haiku, Phase 1)", supported: true },
  { value: "opportunity_score", label: "Opportunity score (rules, $0)", supported: true },
  { value: "why_now", label: "Why Now (Phase 4)", supported: false },
  { value: "opportunity_narrative", label: "Opportunity narrative (Phase 4)", supported: false },
  { value: "trend_narrative", label: "Trend narrative (Phase 3)", supported: false },
  { value: "assignee_narrative", label: "Assignee narrative (Phase 4)", supported: false },
  { value: "score_rerank", label: "Score re-rank (Phase 4)", supported: false },
];

const RUN_MODES: { value: AIRunMode; label: string; help: string }[] = [
  { value: "dev_fixture", label: "Dev Fixture (50)", help: "Deterministic 50-patent fixture. Always safe." },
  { value: "sample", label: "Sample (100)", help: "100 most-recent grants. Safe quick test." },
  { value: "cohort", label: "Cohort", help: "Apply your filters; one-click if est cost is below threshold." },
  { value: "full_batch", label: "Full batch", help: "Apply filters with no limit. Requires typing 'RUN FULL BATCH'." },
];

export default function AIRunsPage() {
  const { data: meta } = useRunMetadata();
  const { data: history, mutate: refreshHistory } = useRunHistory(50);

  const [taskType, setTaskType] = useState<AITaskType>("summary");
  const [runMode, setRunMode] = useState<AIRunMode>("dev_fixture");
  const [cohort, setCohort] = useState<CohortFilter>({});
  const [estimate, setEstimate] = useState<EstimateResponse | null>(null);
  const [estLoading, setEstLoading] = useState(false);
  const [estError, setEstError] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [confirmPhrase, setConfirmPhrase] = useState("");

  async function onEstimate() {
    setEstLoading(true);
    setEstError(null);
    setEstimate(null);
    try {
      const result = await aiRunsApi.estimate({
        task_type: taskType,
        run_mode: runMode,
        cohort,
      });
      setEstimate(result);
    } catch (e) {
      setEstError((e as Error).message);
    } finally {
      setEstLoading(false);
    }
  }

  async function onRun() {
    if (!estimate) return;
    setRunLoading(true);
    setRunError(null);
    try {
      await aiRunsApi.create({
        task_type: taskType,
        run_mode: runMode,
        cohort,
        confirmation_phrase:
          estimate.requires_full_batch_phrase ? confirmPhrase : undefined,
        enqueue: true,
      });
      setConfirmPhrase("");
      setEstimate(null);
      refreshHistory();
    } catch (e) {
      setRunError((e as Error).message);
    } finally {
      setRunLoading(false);
    }
  }

  const fullBatchOk =
    !estimate?.requires_full_batch_phrase || confirmPhrase === FULL_BATCH_PHRASE;
  const phaseUnsupported = !TASK_TYPES.find((t) => t.value === taskType)
    ?.supported;

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Runs</h1>
          <p className="text-sm text-gray-600 mt-1">
            Cost-visible cohort runner. Every LLM call is cached as an{" "}
            <code className="bg-gray-100 px-1 rounded">AIArtifact</code>; replays
            cost $0.
          </p>
        </div>
        {meta && (
          <div className="text-xs text-gray-500 text-right">
            <div>
              <span className="font-medium">user:</span> {meta.default_user_id}
            </div>
            <div>
              <span className="font-medium">llm_mode:</span> {meta.llm_mode}
            </div>
            <div>
              auto-approve ≤ ${meta.auto_approve_threshold_usd.toFixed(0)} ·
              full-batch &gt; ${meta.full_batch_threshold_usd.toFixed(0)}
            </div>
          </div>
        )}
      </header>

      {/* Configure run */}
      <section className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Configure run</h2>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Task type">
            <select
              value={taskType}
              onChange={(e) => setTaskType(e.target.value as AITaskType)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              {TASK_TYPES.map((t) => (
                <option key={t.value} value={t.value} disabled={!t.supported}>
                  {t.label} {t.supported ? "" : "— not yet implemented"}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Run mode">
            <select
              value={runMode}
              onChange={(e) => setRunMode(e.target.value as AIRunMode)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              {RUN_MODES.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {RUN_MODES.find((m) => m.value === runMode)?.help}
            </p>
          </Field>
        </div>

        {/* Cohort filters (only meaningful for cohort + full_batch) */}
        {(runMode === "cohort" || runMode === "full_batch") && (
          <div className="grid grid-cols-3 gap-4 pt-2">
            <Field label="CPC prefix">
              <input
                type="text"
                placeholder="e.g. G06F or H04L"
                value={cohort.cpc_prefix ?? ""}
                onChange={(e) =>
                  setCohort({ ...cohort, cpc_prefix: e.target.value || null })
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </Field>
            <Field label="Grant year from">
              <input
                type="number"
                value={cohort.grant_year_from ?? ""}
                onChange={(e) =>
                  setCohort({
                    ...cohort,
                    grant_year_from: e.target.value
                      ? Number(e.target.value)
                      : null,
                  })
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </Field>
            <Field label="Grant year to">
              <input
                type="number"
                value={cohort.grant_year_to ?? ""}
                onChange={(e) =>
                  setCohort({
                    ...cohort,
                    grant_year_to: e.target.value
                      ? Number(e.target.value)
                      : null,
                  })
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </Field>
            <Field label="Expiry within (days)">
              <input
                type="number"
                placeholder="e.g. 365"
                value={cohort.expiry_within_days ?? ""}
                onChange={(e) =>
                  setCohort({
                    ...cohort,
                    expiry_within_days: e.target.value
                      ? Number(e.target.value)
                      : null,
                  })
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </Field>
            <Field label="Has abstract">
              <select
                value={cohort.has_abstract === undefined || cohort.has_abstract === null ? "" : String(cohort.has_abstract)}
                onChange={(e) =>
                  setCohort({
                    ...cohort,
                    has_abstract:
                      e.target.value === ""
                        ? null
                        : e.target.value === "true",
                  })
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">any</option>
                <option value="true">yes</option>
                <option value="false">no</option>
              </select>
            </Field>
            <Field label="Has summary">
              <select
                value={cohort.has_summary === undefined || cohort.has_summary === null ? "" : String(cohort.has_summary)}
                onChange={(e) =>
                  setCohort({
                    ...cohort,
                    has_summary:
                      e.target.value === ""
                        ? null
                        : e.target.value === "true",
                  })
                }
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">any</option>
                <option value="true">yes</option>
                <option value="false">no</option>
              </select>
            </Field>
            {runMode === "cohort" && (
              <Field label="Limit">
                <input
                  type="number"
                  placeholder="e.g. 500"
                  value={cohort.limit ?? ""}
                  onChange={(e) =>
                    setCohort({
                      ...cohort,
                      limit: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </Field>
            )}
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={onEstimate}
            disabled={estLoading || phaseUnsupported}
            className="rounded-md bg-primary-600 text-white px-4 py-2 text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
          >
            {estLoading ? "Estimating…" : "Preview cost"}
          </button>
          {phaseUnsupported && (
            <span className="text-xs text-amber-700">
              Run creation for this task type lands in a later phase.
            </span>
          )}
          {estError && (
            <span className="text-xs text-red-600">{estError}</span>
          )}
        </div>
      </section>

      {/* Estimate preview */}
      {estimate && (
        <section className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
          <div className="flex items-baseline justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Cost preview</h2>
            <div className="text-2xl font-bold text-gray-900">
              ${estimate.est_cost_usd.toFixed(4)}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 text-sm">
            <Stat label="Cohort size" value={estimate.cohort_size.toLocaleString()} />
            <Stat label="Already cached" value={estimate.cached_count.toLocaleString()} />
            <Stat label="Will call LLM" value={estimate.uncached_count.toLocaleString()} />
            <Stat label="Est input tokens" value={estimate.est_input_tokens.toLocaleString()} />
            <Stat label="Est output tokens" value={estimate.est_output_tokens.toLocaleString()} />
            <Stat label="Model" value={estimate.model} />
            <Stat label="Prompt" value={`${estimate.prompt_name} v${estimate.prompt_version}`} />
            <Stat label="prompt_hash" value={estimate.prompt_hash.slice(0, 12) + "…"} />
            <Stat
              label="7d cache hit-rate"
              value={`${(estimate.expected_cache_hit_rate_7d * 100).toFixed(1)}%`}
            />
          </div>

          {estimate.requires_full_batch_phrase && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3 space-y-2">
              <p className="text-sm text-red-800 font-medium">
                This run is large enough to require typing &ldquo;{FULL_BATCH_PHRASE}&rdquo; below.
              </p>
              <input
                type="text"
                value={confirmPhrase}
                onChange={(e) => setConfirmPhrase(e.target.value)}
                placeholder={FULL_BATCH_PHRASE}
                className="w-full rounded-md border border-red-300 px-3 py-2 text-sm font-mono"
              />
            </div>
          )}

          {!estimate.requires_full_batch_phrase &&
            estimate.requires_confirmation && (
              <div className="bg-amber-50 border border-amber-200 rounded-md p-3 text-sm text-amber-900">
                Estimated cost (${estimate.est_cost_usd.toFixed(4)}) exceeds the
                auto-approve threshold ($
                {estimate.auto_approve_threshold_usd.toFixed(2)}). Review before
                clicking Run.
              </div>
            )}

          <div className="flex items-center gap-3">
            <button
              onClick={onRun}
              disabled={runLoading || !fullBatchOk}
              className="rounded-md bg-emerald-600 text-white px-4 py-2 text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
            >
              {runLoading ? "Starting…" : "Run"}
            </button>
            <button
              onClick={() => setEstimate(null)}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
            >
              Cancel
            </button>
            {runError && <span className="text-xs text-red-600">{runError}</span>}
          </div>
        </section>
      )}

      {/* Run history */}
      <section className="bg-white rounded-lg border border-gray-200 p-6 space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Recent runs</h2>
          <span className="text-xs text-gray-500">
            {history?.total ?? 0} total
          </span>
        </div>
        <RunHistoryTable items={history?.items ?? []} />
      </section>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-gray-700 uppercase tracking-wide">
        {label}
      </span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-gray-500 uppercase tracking-wide">
        {label}
      </div>
      <div className="text-sm font-mono text-gray-900 mt-1 break-all">
        {value}
      </div>
    </div>
  );
}

function RunHistoryTable({ items }: { items: RunSummary[] }) {
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-6 text-center">
        No runs yet. Configure one above and click <strong>Run</strong> to start.
      </p>
    );
  }
  return (
    <table className="w-full text-sm">
      <thead className="text-xs text-gray-500 uppercase">
        <tr className="border-b border-gray-200">
          <th className="text-left py-2 w-8"></th>
          <th className="text-left py-2">When</th>
          <th className="text-left py-2">Task</th>
          <th className="text-left py-2">Mode</th>
          <th className="text-left py-2">Status</th>
          <th className="text-right py-2">Cohort</th>
          <th className="text-right py-2">Cached</th>
          <th className="text-right py-2">Est $</th>
          <th className="text-right py-2">Actual $</th>
          <th className="text-right py-2">Done / Fail</th>
        </tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <>
            <tr
              key={r.id}
              className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
              onClick={() => setExpandedRunId(expandedRunId === r.id ? null : r.id)}
            >
              <td className="py-2 text-gray-400">
                <span className="inline-block w-4">
                  {expandedRunId === r.id ? "▼" : "▶"}
                </span>
              </td>
              <td className="py-2 text-gray-600">
                {formatDate(r.created_at)}
              </td>
              <td className="py-2 font-medium">{r.task_type}</td>
              <td className="py-2 text-gray-600">{r.run_mode}</td>
              <td className="py-2">
                <StatusPill status={r.status} />
              </td>
              <td className="py-2 text-right">{r.cohort_size}</td>
              <td className="py-2 text-right">{r.cached_count}</td>
              <td className="py-2 text-right font-mono">
                ${r.est_cost_usd.toFixed(4)}
              </td>
              <td className="py-2 text-right font-mono">
                ${r.actual_cost_usd.toFixed(4)}
              </td>
              <td className="py-2 text-right">
                {r.completed_count} / {r.failed_count}
              </td>
            </tr>
            {expandedRunId === r.id && (
              <tr>
                <td colSpan={10} className="bg-gray-50 border-b border-gray-100">
                  <ArtifactPanel runId={r.id} />
                </td>
              </tr>
            )}
          </>
        ))}
      </tbody>
    </table>
  );
}

function ArtifactPanel({ runId }: { runId: string }) {
  const { data, isLoading } = useRunArtifacts(runId, 50, 0);
  if (isLoading) return <div className="p-4 text-sm text-gray-500">Loading artifacts…</div>;
  if (!data || data.items.length === 0) return <div className="p-4 text-sm text-gray-500">No artifacts found.</div>;

  const complete = data.items.filter((a) => a.status === "complete").length;
  const failed = data.items.filter((a) => a.status === "failed").length;
  const pending = data.items.length - complete - failed;
  const totalTokens = data.items.reduce((s, a) => s + a.input_tokens + a.output_tokens, 0);
  const totalCost = data.items.reduce((s, a) => s + a.actual_cost_usd, 0);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-4 text-xs text-gray-600">
        <span><strong>{data.total}</strong> artifacts</span>
        <span className="text-emerald-700">{complete} complete</span>
        {failed > 0 && <span className="text-red-700">{failed} failed</span>}
        {pending > 0 && <span className="text-gray-500">{pending} pending</span>}
        <span>{totalTokens.toLocaleString()} tokens</span>
        <span>${totalCost.toFixed(4)}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="text-gray-500 uppercase">
            <tr className="border-b border-gray-200">
              <th className="text-left py-1">Patent</th>
              <th className="text-left py-1">Type</th>
              <th className="text-left py-1">Status</th>
              <th className="text-right py-1">Tokens</th>
              <th className="text-right py-1">Cost</th>
              <th className="text-left py-1">Preview</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((a) => (
              <ArtifactRow key={a.id} artifact={a} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ArtifactRow({ artifact }: { artifact: ArtifactSummary }) {
  const [showJson, setShowJson] = useState(false);
  return (
    <tr className="border-b border-gray-100">
      <td className="py-1 font-mono text-gray-600">
        {artifact.patent_publication_id ? artifact.patent_publication_id.slice(0, 8) + "…" : "—"}
      </td>
      <td className="py-1">{artifact.artifact_type}</td>
      <td className="py-1"><StatusPill status={artifact.status} /></td>
      <td className="py-1 text-right">{(artifact.input_tokens + artifact.output_tokens).toLocaleString()}</td>
      <td className="py-1 text-right font-mono">${artifact.actual_cost_usd.toFixed(4)}</td>
      <td className="py-1">
        {artifact.content_json_preview ? (
          <button
            onClick={(e) => { e.stopPropagation(); setShowJson(!showJson); }}
            className="text-primary-600 hover:underline"
          >
            {showJson ? "Hide JSON" : "View JSON"}
          </button>
        ) : (
          <span className="text-gray-400">No preview</span>
        )}
        {showJson && artifact.content_json_preview && (
          <pre className="mt-1 p-2 bg-gray-800 text-gray-100 rounded text-[10px] overflow-auto max-h-40 max-w-md">
            {JSON.stringify(artifact.content_json_preview, null, 2)}
          </pre>
        )}
      </td>
    </tr>
  );
}

function StatusPill({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    pending: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    succeeded: "bg-emerald-100 text-emerald-700",
    failed: "bg-red-100 text-red-700",
    cancelled: "bg-amber-100 text-amber-800",
  };
  const cls = colorMap[status] ?? "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}
