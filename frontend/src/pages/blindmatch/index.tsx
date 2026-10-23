// Owner: Dev D
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useIdentity } from "../../lib/roles";

interface BlindMatchCase {
  id: string;
  record_a: string;
  record_b: string;
  institution_a_id: string;
  institution_b_id: string;
  dice: number;
  fields_compared: string[];
  status: string;
  review_case_id: string | null;
}

function formatScore(score: number) {
  if (!Number.isFinite(score)) return "Unavailable";
  return score.toFixed(3);
}

function scorePercent(score: number) {
  if (!Number.isFinite(score)) return 0;
  const percent = score <= 1 ? score * 100 : score;
  return Math.max(0, Math.min(100, percent));
}

function statusStyle(status: string) {
  const normalized = status.toLowerCase();

  if (normalized.includes("match") || normalized.includes("review")) {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }

  if (
    normalized.includes("clear") ||
    normalized.includes("dismiss") ||
    normalized.includes("no_match")
  ) {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }

  return "border-slate-200 bg-slate-100 text-slate-700";
}

export default function BlindMatchPage() {
  const { role } = useIdentity();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["blind-match-cases", role],
    queryFn: () => api<BlindMatchCase[]>("/blind-match/cases"),
  });

  const cases = Array.isArray(query.data) ? query.data : [];
  const selectedCase = cases.find((item) => item.id === selectedId) ?? cases[0];

  const averageScore =
    cases.length > 0
      ? cases.reduce((total, item) => total + item.dice, 0) / cases.length
      : null;

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl bg-slate-950 text-white">
        <div className="grid gap-6 p-6 sm:p-8 md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <div className="mb-3 flex items-center gap-2">
              <span className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-cyan-300">
                Privacy-preserving matching
              </span>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Blind Match
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
              Explore potential cross-institution identity matches using
              similarity scores, without displaying student identity details.
            </p>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/5 p-5 md:min-w-36">
            <p className="text-sm text-slate-400">Cases returned</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums">
              {query.isSuccess ? cases.length : "—"}
            </p>
            <p className="mt-1 text-xs text-slate-400">From the cases API</p>
          </div>
        </div>

        <div className="grid grid-cols-1 border-t border-white/10 sm:grid-cols-3">
          <div className="border-b border-white/10 p-4 sm:border-b-0 sm:border-r">
            <p className="text-xs uppercase tracking-wider text-slate-400">
              Matching method
            </p>
            <p className="mt-1 font-medium">Dice similarity</p>
          </div>
          <div className="border-b border-white/10 p-4 sm:border-b-0 sm:border-r">
            <p className="text-xs uppercase tracking-wider text-slate-400">
              Identity exposure
            </p>
            <p className="mt-1 font-medium">No identity fields shown</p>
          </div>
          <div className="p-4">
            <p className="text-xs uppercase tracking-wider text-slate-400">
              Average returned score
            </p>
            <p className="mt-1 font-medium tabular-nums">
              {averageScore === null ? "—" : formatScore(averageScore)}
            </p>
          </div>
        </div>
      </section>

      {query.isPending && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
          <p className="mt-4 font-medium text-slate-800">Loading match cases</p>
          <p className="mt-1 text-sm text-slate-500">
            Retrieving the available case records.
          </p>
        </div>
      )}

      {query.isError && (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-5"
        >
          <h2 className="font-semibold text-red-900">
            Could not load match cases
          </h2>
          <p className="mt-1 text-sm text-red-800">
            Check your API connection and demo role, then try again.
          </p>
          <button
            type="button"
            onClick={() => void query.refetch()}
            className="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800"
          >
            Retry request
          </button>
        </div>
      )}

      {query.isSuccess && cases.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-xl text-slate-500">
            ↔
          </div>
          <h2 className="mt-4 text-lg font-semibold text-slate-900">
            No match cases yet
          </h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
            No cases were returned by the API. When matching cases become
            available, they will appear here.
          </p>
        </div>
      )}

      {query.isSuccess && cases.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <section className="min-w-0 space-y-3">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  Match cases
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Select a case to inspect its score and status.
                </p>
              </div>
              <span className="text-xs text-slate-500">
                {cases.length} total
              </span>
            </div>

            <div className="space-y-3">
              {cases.map((item) => {
                const isSelected = selectedCase?.id === item.id;

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSelectedId(item.id)}
                    aria-pressed={isSelected}
                    className={`w-full rounded-xl border p-4 text-left transition ${
                      isSelected
                        ? "border-blue-500 bg-blue-50/70 ring-1 ring-blue-500"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="break-all text-sm font-semibold text-slate-900">
                          {item.id}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          Similarity score
                        </p>
                      </div>
                      <span
                        className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium ${statusStyle(item.status)}`}
                      >
                        {item.status.replaceAll("_", " ")}
                      </span>
                    </div>

                    <div className="mt-4 flex items-center gap-3">
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-blue-600 transition-all"
                          style={{ width: `${scorePercent(item.dice)}%` }}
                        />
                      </div>
                      <span className="min-w-14 text-right text-sm font-semibold tabular-nums text-slate-800">
                        {formatScore(item.dice)}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="min-w-0 space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Comparison details
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Case-level information returned by the matching service.
              </p>
            </div>

            {selectedCase && (
              <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Selected case
                    </p>
                    <h3 className="mt-1 break-all text-lg font-semibold text-slate-900">
                      {selectedCase.id}
                    </h3>
                  </div>
                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusStyle(selectedCase.status)}`}
                  >
                    {selectedCase.status.replaceAll("_", " ")}
                  </span>
                </div>

                <div className="rounded-xl bg-slate-50 p-5">
                  <p className="text-sm font-medium text-slate-600">
                    Returned Dice score
                  </p>
                  <p className="mt-2 text-4xl font-semibold tracking-tight text-slate-950 tabular-nums">
                    {formatScore(selectedCase.dice)}
                  </p>
                  <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-full rounded-full bg-blue-600"
                      style={{
                        width: `${scorePercent(selectedCase.dice)}%`,
                      }}
                    />
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    The score is displayed as returned by the matching service.
                    It represents similarity, not the probability that two
                    records belong to the same person. Review the case before
                    making a decision.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs text-slate-500">Case reference</p>
                    <p className="mt-1 break-all text-sm font-semibold text-slate-900">
                      {selectedCase.id}
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs text-slate-500">Current status</p>
                    <p className="mt-1 break-words text-sm font-semibold capitalize text-slate-900">
                      {selectedCase.status.replaceAll("_", " ")}
                    </p>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs text-slate-500">Record A</p>
                    <p className="mt-1 break-all text-sm font-medium text-slate-900">
                      {selectedCase.record_a}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs text-slate-500">Record B</p>
                    <p className="mt-1 break-all text-sm font-medium text-slate-900">
                      {selectedCase.record_b}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs text-slate-500">Institution A</p>
                    <p className="mt-1 break-all text-sm font-medium text-slate-900">
                      {selectedCase.institution_a_id}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs text-slate-500">Institution B</p>
                    <p className="mt-1 break-all text-sm font-medium text-slate-900">
                      {selectedCase.institution_b_id}
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 p-4">
                  <h4 className="text-sm font-semibold text-slate-900">
                    Fields compared
                  </h4>

                  {selectedCase.fields_compared.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {selectedCase.fields_compared.map((field) => (
                        <span
                          key={field}
                          className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
                        >
                          {field}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-slate-500">
                      No compared fields were returned.
                    </p>
                  )}
                </div>

                <div className="rounded-xl border border-slate-200 p-4">
                  <p className="text-xs text-slate-500">
                    Review case reference
                  </p>
                  <p className="mt-1 break-all text-sm font-medium text-slate-900">
                    {selectedCase.review_case_id ??
                      "Not linked to a review case"}
                  </p>
                </div>

                <div className="flex items-start gap-3 rounded-xl border border-cyan-100 bg-cyan-50 p-4">
                  <span className="mt-0.5 text-cyan-800" aria-hidden="true">
                    ⓘ
                  </span>
                  <p className="text-sm leading-6 text-cyan-950">
                    This view intentionally excludes student identity
                    information. A similarity score alone is not proof of a
                    duplicate; review the evidence and the matching service's
                    configured threshold before making a decision.
                  </p>
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      <p className="text-xs leading-5 text-slate-500">
        API: <code>/blind-match/cases</code>. Scores and statuses are displayed
        as returned by the service; this screen does not perform identity
        matching itself.
      </p>
    </div>
  );
}
