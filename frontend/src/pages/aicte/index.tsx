// Owner: Dev D

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "../../lib/api-types";
import { api } from "../../lib/api";
import { useIdentity } from "../../lib/roles";
import Reports from "./Reports";

type ReviewCase = components["schemas"]["ReviewCase"];
type IntegrityRanking = components["schemas"]["IntegrityRanking"];
type IntegrityDetail = components["schemas"]["IntegrityDetail"];
type AuditVerifyResult = components["schemas"]["AuditVerifyResult"];
type ResolveRequest = components["schemas"]["ResolveRequest"];

const panel = "rounded-xl border border-slate-200 bg-white p-5 shadow-sm";
const button =
  "rounded-lg px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50";
const primaryButton = `${button} bg-slate-900 text-white hover:bg-slate-700`;
const secondaryButton = `${button} border border-slate-300 bg-white text-slate-700 hover:bg-slate-50`;
const field =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

function statusStyle(status: string) {
  if (status === "open") return "bg-amber-100 text-amber-800";
  if (status === "confirmed") return "bg-green-100 text-green-800";
  if (status === "dismissed") return "bg-slate-100 text-slate-700";
  return "bg-blue-100 text-blue-800";
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
    >
      {message}
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail: string;
}) {
  return (
    <div className={panel}>
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
        {value}
      </p>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

export default function AictePage() {
  const { role } = useIdentity();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState("open");
  const [kindFilter, setKindFilter] = useState("all");
  const [selectedCase, setSelectedCase] = useState<ReviewCase | null>(null);
  const [decision, setDecision] =
    useState<ResolveRequest["status"]>("confirmed");
  const [reviewerNote, setReviewerNote] = useState("");
  const [selectedInstitution, setSelectedInstitution] = useState<string | null>(
    null,
  );
  const [auditResult, setAuditResult] = useState<AuditVerifyResult | null>(
    null,
  );

  const casesQuery = useQuery({
    queryKey: ["aicte-review-cases", role, statusFilter, kindFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (statusFilter !== "all") params.set("status", statusFilter);
      if (kindFilter !== "all") params.set("kind", kindFilter);
      const suffix = params.size ? `?${params.toString()}` : "";
      return api<ReviewCase[]>(`/review-cases${suffix}`);
    },
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });

  const openCasesQuery = useQuery({
    queryKey: ["aicte-open-review-cases", role],
    queryFn: () => api<ReviewCase[]>("/review-cases?status=open"),
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });

  const rankingsQuery = useQuery({
    queryKey: ["aicte-integrity-rankings", role],
    queryFn: () => api<IntegrityRanking[]>("/integrity/institutions"),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const detailQuery = useQuery({
    queryKey: ["aicte-institution-integrity", selectedInstitution, role],
    queryFn: () =>
      api<IntegrityDetail>(`/integrity/institutions/${selectedInstitution}`),
    enabled: Boolean(selectedInstitution),
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ResolveRequest }) =>
      api<ReviewCase>(`/review-cases/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      setSelectedCase(null);
      setReviewerNote("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["aicte-review-cases"] }),
        queryClient.invalidateQueries({
          queryKey: ["aicte-open-review-cases"],
        }),
      ]);
    },
  });

  const auditMutation = useMutation({
    mutationFn: () => api<AuditVerifyResult>("/audit/verify"),
    onSuccess: (result) => setAuditResult(result),
  });

  const cases = casesQuery.data ?? [];
  const rankings = rankingsQuery.data ?? [];
  const openCount = openCasesQuery.data?.length ?? 0;
  const highAnomalyCount = rankings.filter(
    (item) => item.anomaly_score >= 0.7,
  ).length;
  const averageScore = rankings.length
    ? Math.round(
        rankings.reduce((sum, item) => sum + item.integrity_score, 0) /
          rankings.length,
      )
    : null;

  async function refreshDashboard() {
    await Promise.all([
      casesQuery.refetch(),
      openCasesQuery.refetch(),
      rankingsQuery.refetch(),
    ]);
  }

  function submitDecision(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCase || !reviewerNote.trim()) return;

    resolveMutation.mutate({
      id: selectedCase.id,
      payload: {
        status: decision,
        note: reviewerNote.trim(),
      },
    });
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
            APAAR Integrity Platform · SIMULATED
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
            AICTE Integrity Dashboard
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            Monitor integrity exceptions, review institution risk signals, and
            record auditable decisions.
          </p>
          <p className="mt-2 text-xs text-slate-500">
            Review queue refreshes every 15 seconds. Rankings refresh every 30
            seconds.
          </p>
        </div>
        <button
          type="button"
          className={secondaryButton}
          onClick={() => void refreshDashboard()}
          disabled={casesQuery.isFetching || rankingsQuery.isFetching}
        >
          {casesQuery.isFetching || rankingsQuery.isFetching
            ? "Refreshing…"
            : "Refresh dashboard"}
        </button>
      </header>

      {(casesQuery.isError ||
        openCasesQuery.isError ||
        rankingsQuery.isError) && (
        <ErrorMessage message="Some dashboard data could not be loaded. Check your API connection and try refreshing." />
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Open review cases"
          value={openCasesQuery.isLoading ? "—" : openCount}
          detail="Cases awaiting a decision"
        />
        <Metric
          label="Institutions ranked"
          value={rankingsQuery.isLoading ? "—" : rankings.length}
          detail="Integrity ranking results"
        />
        <Metric
          label="High anomaly scores"
          value={rankingsQuery.isLoading ? "—" : highAnomalyCount}
          detail="Anomaly score ≥ 0.70"
        />
        <Metric
          label="Average integrity score"
          value={averageScore === null ? "—" : `${averageScore}/100`}
          detail="Across ranked institutions"
        />
      </section>

      <section className={panel}>
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">
              Exception queue
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Review cases and record a decision with a mandatory note.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <select
              aria-label="Filter cases by status"
              className={field}
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="open">Open</option>
              <option value="confirmed">Confirmed</option>
              <option value="dismissed">Dismissed</option>
              <option value="correction_requested">Correction requested</option>
              <option value="all">All statuses</option>
            </select>
            <select
              aria-label="Filter cases by type"
              className={field}
              value={kindFilter}
              onChange={(event) => setKindFilter(event.target.value)}
            >
              <option value="all">All types</option>
              <option value="intake_overrun">Intake overrun</option>
              <option value="blind_match">Blind match</option>
              <option value="dispute">Dispute</option>
              <option value="signal">Integrity signal</option>
            </select>
          </div>
        </div>

        {casesQuery.isLoading ? (
          <p className="py-8 text-sm text-slate-500">Loading review cases…</p>
        ) : cases.length === 0 ? (
          <div className="mt-5 rounded-lg border border-dashed border-slate-300 p-8 text-center">
            <p className="font-medium text-slate-800">No review cases found</p>
            <p className="mt-1 text-sm text-slate-500">
              Try another status or case-type filter.
            </p>
          </div>
        ) : (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="pb-3 pr-4 font-medium">Case</th>
                  <th className="pb-3 pr-4 font-medium">Type</th>
                  <th className="pb-3 pr-4 font-medium">Institution ID</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  <th className="pb-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="py-4 pr-4">
                      <p className="font-medium text-slate-900">{item.title}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {item.id.slice(0, 8)}
                      </p>
                    </td>
                    <td className="py-4 pr-4 capitalize text-slate-700">
                      {item.kind.replaceAll("_", " ")}
                    </td>
                    <td className="py-4 pr-4 font-mono text-xs text-slate-600">
                      {item.institution_id.slice(0, 12)}…
                      <button
                        type="button"
                        className="ml-2 text-blue-700 underline"
                        onClick={() =>
                          setSelectedInstitution(item.institution_id)
                        }
                      >
                        Inspect
                      </button>
                    </td>
                    <td className="py-4 pr-4">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusStyle(item.status)}`}
                      >
                        {item.status.replaceAll("_", " ")}
                      </span>
                    </td>
                    <td className="py-4">
                      {item.status === "open" ? (
                        <button
                          type="button"
                          className={secondaryButton}
                          onClick={() => {
                            setSelectedCase(item);
                            setReviewerNote("");
                            setDecision("confirmed");
                            resolveMutation.reset();
                          }}
                        >
                          Review
                        </button>
                      ) : (
                        <span className="text-xs text-slate-500">Resolved</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {casesQuery.isError && (
          <div className="mt-4">
            <ErrorMessage message="Unable to load the exception queue." />
          </div>
        )}
      </section>

      <section className={panel}>
        <div>
          <h2 className="text-lg font-semibold text-slate-950">
            Integrity Score rankings
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Institutions are returned in anomaly-priority order by the API.
          </p>
        </div>

        {rankingsQuery.isLoading ? (
          <p className="py-8 text-sm text-slate-500">Loading rankings…</p>
        ) : rankings.length === 0 ? (
          <p className="py-8 text-sm text-slate-500">
            No institution rankings available.
          </p>
        ) : (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[650px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="pb-3 pr-4 font-medium">Rank</th>
                  <th className="pb-3 pr-4 font-medium">Institution</th>
                  <th className="pb-3 pr-4 font-medium">Integrity score</th>
                  <th className="pb-3 pr-4 font-medium">Anomaly score</th>
                  <th className="pb-3 font-medium">Top signals</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((item) => (
                  <tr
                    key={item.institution_id}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="py-4 pr-4 font-semibold text-slate-700">
                      #{item.rank}
                    </td>
                    <td className="py-4 pr-4">
                      <button
                        type="button"
                        className="text-left font-medium text-blue-700 hover:underline"
                        onClick={() =>
                          setSelectedInstitution(item.institution_id)
                        }
                      >
                        {item.institution_name}
                      </button>
                      <p className="mt-1 text-xs text-slate-500">
                        AICTE code: {item.aicte_code}
                      </p>
                    </td>
                    <td className="py-4 pr-4">
                      <span className="font-semibold text-slate-900">
                        {item.integrity_score}/100
                      </span>
                    </td>
                    <td className="py-4 pr-4">
                      <span
                        className={
                          item.anomaly_score >= 0.7
                            ? "font-semibold text-red-700"
                            : "text-slate-700"
                        }
                      >
                        {item.anomaly_score.toFixed(2)}
                      </span>
                    </td>
                    <td className="py-4 text-slate-600">
                      {item.top_signals.length
                        ? item.top_signals.join(", ")
                        : "No top signals returned"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {rankingsQuery.isError && (
          <div className="mt-4">
            <ErrorMessage message="Unable to load integrity rankings." />
          </div>
        )}
      </section>

      <section className={panel}>
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">
              Audit-chain verification
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Recompute the audit hash chain to check its integrity.
            </p>
          </div>
          <button
            type="button"
            className={primaryButton}
            disabled={auditMutation.isPending}
            onClick={() => auditMutation.mutate()}
          >
            {auditMutation.isPending ? "Verifying…" : "Verify audit chain"}
          </button>
        </div>

        {auditMutation.isError && (
          <div className="mt-4">
            <ErrorMessage message="Audit verification failed. Check permissions and the API response." />
          </div>
        )}

        {auditResult && (
          <div
            role={auditResult.ok ? "status" : "alert"}
            className={`mt-4 rounded-lg border p-4 ${
              auditResult.ok
                ? "border-green-200 bg-green-50 text-green-900"
                : "border-red-300 bg-red-50 text-red-900"
            }`}
          >
            <p className="font-semibold">
              {auditResult.ok
                ? "Audit chain verified"
                : "WARNING: Audit-chain tampering detected"}
            </p>
            <p className="mt-1 text-sm">
              Entries checked: {auditResult.checked}
            </p>
            {!auditResult.ok && (
              <p className="mt-1 text-sm">
                First broken index:{" "}
                {auditResult.first_broken_index ?? "Not provided by the API"}
              </p>
            )}
          </div>
        )}
      </section>

      <Reports rankings={rankings} />

      {selectedInstitution && (
        <section className={panel}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">
                Institution integrity details
              </h2>
              <p className="mt-1 break-all font-mono text-xs text-slate-500">
                {selectedInstitution}
              </p>
            </div>
            <button
              type="button"
              className={secondaryButton}
              onClick={() => setSelectedInstitution(null)}
            >
              Close
            </button>
          </div>

          {detailQuery.isLoading ? (
            <p className="py-6 text-sm text-slate-500">
              Loading institution signals…
            </p>
          ) : detailQuery.isError ? (
            <div className="mt-4">
              <ErrorMessage message="Could not load integrity details for this institution." />
            </div>
          ) : detailQuery.data ? (
            <div className="mt-5 space-y-5">
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-sm text-slate-500">Integrity score</p>
                <p className="mt-1 text-3xl font-semibold text-slate-950">
                  {detailQuery.data.integrity_score}/100
                </p>
              </div>

              <div>
                <h3 className="font-medium text-slate-900">Score components</h3>
                <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(detailQuery.data.components).map(
                    ([name, value]) => (
                      <div
                        key={name}
                        className="rounded-lg border border-slate-200 p-3"
                      >
                        <p className="text-sm capitalize text-slate-500">
                          {name.replaceAll("_", " ")}
                        </p>
                        <p className="mt-1 text-lg font-semibold text-slate-900">
                          {value}
                        </p>
                      </div>
                    ),
                  )}
                </div>
              </div>

              <div>
                <h3 className="font-medium text-slate-900">
                  Integrity signals
                </h3>
                {detailQuery.data.signals.length === 0 ? (
                  <p className="mt-2 text-sm text-slate-500">
                    No signals returned.
                  </p>
                ) : (
                  <ul className="mt-3 space-y-2">
                    {detailQuery.data.signals.map((signal, index) => (
                      <li
                        key={`${signal.code}-${index}`}
                        className="rounded-lg border border-slate-200 p-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-medium text-slate-900">
                            {signal.code}
                          </span>
                          <span
                            className={`rounded-full px-2 py-1 text-xs ${statusStyle(signal.severity)}`}
                          >
                            {signal.severity}
                          </span>
                        </div>
                        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs text-slate-600">
                          {JSON.stringify(signal.evidence, null, 2)}
                        </pre>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <h3 className="font-medium text-slate-900">
                  Anomaly explanation
                </h3>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-4 text-xs text-slate-700">
                  {JSON.stringify(detailQuery.data.anomaly, null, 2)}
                </pre>
              </div>
            </div>
          ) : null}
        </section>
      )}

      {selectedCase && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 p-0 sm:items-center sm:p-4">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-dialog-title"
            className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
                  Review case
                </p>
                <h2
                  id="review-dialog-title"
                  className="mt-1 text-xl font-semibold text-slate-950"
                >
                  {selectedCase.title}
                </h2>
              </div>
              <button
                type="button"
                className={secondaryButton}
                onClick={() => {
                  setSelectedCase(null);
                  resolveMutation.reset();
                }}
              >
                Close
              </button>
            </div>

            <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm">
              <p>
                <span className="text-slate-500">Type:</span>{" "}
                {selectedCase.kind.replaceAll("_", " ")}
              </p>
              <p className="mt-1 break-all">
                <span className="text-slate-500">Case ID:</span>{" "}
                {selectedCase.id}
              </p>
              <p className="mt-1 break-all">
                <span className="text-slate-500">Institution ID:</span>{" "}
                {selectedCase.institution_id}
              </p>
            </div>

            <div className="mt-4">
              <h3 className="font-medium text-slate-900">Case evidence</h3>
              <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-200 p-3 text-xs text-slate-700">
                {JSON.stringify(selectedCase.evidence, null, 2)}
              </pre>
            </div>

            <form onSubmit={submitDecision} className="mt-5 space-y-4">
              <div>
                <label
                  htmlFor="decision"
                  className="mb-1 block text-sm font-medium text-slate-700"
                >
                  Decision
                </label>
                <select
                  id="decision"
                  className={field}
                  value={decision}
                  onChange={(event) =>
                    setDecision(event.target.value as ResolveRequest["status"])
                  }
                >
                  <option value="confirmed">Confirm finding</option>
                  <option value="dismissed">Dismiss finding</option>
                  <option value="correction_requested">
                    Request correction
                  </option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="reviewer-note"
                  className="mb-1 block text-sm font-medium text-slate-700"
                >
                  Reviewer note <span className="text-red-600">*</span>
                </label>
                <textarea
                  id="reviewer-note"
                  className={field}
                  rows={4}
                  required
                  minLength={1}
                  value={reviewerNote}
                  onChange={(event) => setReviewerNote(event.target.value)}
                  placeholder="Explain the evidence and rationale for this decision."
                />
                <p className="mt-1 text-xs text-slate-500">
                  A non-empty note is required for every decision.
                </p>
              </div>

              {resolveMutation.isError && (
                <ErrorMessage message="The decision could not be saved. Check the API error and try again." />
              )}

              {resolveMutation.isSuccess && (
                <p role="status" className="text-sm text-green-700">
                  Decision saved.
                </p>
              )}

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className={secondaryButton}
                  onClick={() => {
                    setSelectedCase(null);
                    resolveMutation.reset();
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={primaryButton}
                  disabled={resolveMutation.isPending || !reviewerNote.trim()}
                >
                  {resolveMutation.isPending ? "Saving…" : "Save decision"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}
