// Owner: Dev D
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { components } from "../../lib/api-types";
import { api } from "../../lib/api";
import { useIdentity } from "../../lib/roles";
import UploadWizard from "./UploadWizard";
import StudentRegistry from "./StudentRegistry";
import PostLockEditRequests from "./PostLockEditRequests";

type SeatLedger = components["schemas"]["SeatLedger"];
type ProgrammeLedger = components["schemas"]["ProgrammeLedger"];
type PoolLedger = components["schemas"]["PoolLedger"];
type Batch = components["schemas"]["Batch"];
type BatchList = components["schemas"]["BatchList"];
type ValidationIssue = components["schemas"]["ValidationIssue"];

const poolLabels: Record<PoolLedger["pool"], string> = {
  regular: "Regular",
  tfw: "TFW",
  fn_oci_pio: "FN / OCI / PIO",
  nri: "NRI",
};

const statusStyles: Record<Batch["status"], string> = {
  uploaded: "bg-slate-100 text-slate-700",
  mapped: "bg-blue-100 text-blue-800",
  validated: "bg-emerald-100 text-emerald-800",
  committed: "bg-indigo-100 text-indigo-800",
  failed: "bg-red-100 text-red-800",
};

const severityStyles: Record<ValidationIssue["severity"], string> = {
  error: "bg-red-100 text-red-800",
  warning: "bg-amber-100 text-amber-800",
  review: "bg-violet-100 text-violet-800",
  info: "bg-sky-100 text-sky-800",
};

function Metric({
  label,
  value,
  description,
}: {
  label: string;
  value: number;
  description: string;
}) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-slate-900">
        {value.toLocaleString()}
      </p>
      <p className="mt-1 text-xs text-slate-500">{description}</p>
    </article>
  );
}

function BatchHistory({ institutionId }: { institutionId: string }) {
  const [offset, setOffset] = useState(0);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const limit = 10;

  const batchesQuery = useQuery({
    queryKey: ["institution-batches", institutionId, offset],
    queryFn: () => api<BatchList>(`/batches?limit=${limit}&offset=${offset}`),
  });

  const issuesQuery = useQuery({
    queryKey: ["batch-issues", selectedBatchId],
    queryFn: () => api<ValidationIssue[]>(`/batches/${selectedBatchId}/issues`),
    enabled: Boolean(selectedBatchId),
  });

  const data = batchesQuery.data;
  const total = data?.total ?? 0;
  const items = data?.items ?? [];

  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Batch History
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Previous admission uploads and their validation status.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void batchesQuery.refetch()}
          disabled={batchesQuery.isFetching}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
        >
          {batchesQuery.isFetching ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {batchesQuery.isPending ? (
        <p className="py-6 text-sm text-slate-500">Loading batch history…</p>
      ) : batchesQuery.isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <p>Could not load batch history.</p>
          <button
            type="button"
            onClick={() => void batchesQuery.refetch()}
            className="mt-2 font-medium underline"
          >
            Retry
          </button>
        </div>
      ) : items.length === 0 ? (
        <p className="rounded-lg bg-slate-50 p-6 text-center text-sm text-slate-500">
          No admission uploads found yet.
        </p>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-3 font-medium">File</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                  <th className="px-3 py-3 text-right font-medium">Rows</th>
                  <th className="px-3 py-3 text-right font-medium">Errors</th>
                  <th className="px-3 py-3 text-right font-medium">Warnings</th>
                  <th className="px-3 py-3 font-medium">Uploaded</th>
                  <th className="px-3 py-3 font-medium">Issues</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((batch) => (
                  <tr key={batch.id} className="align-top hover:bg-slate-50">
                    <td className="max-w-64 break-words px-3 py-4">
                      <p className="font-medium text-slate-900">
                        {batch.file_name}
                      </p>
                      {batch.parent_batch_id && (
                        <p className="mt-1 text-xs text-slate-500">
                          Correction batch
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-4">
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-medium capitalize ${statusStyles[batch.status]}`}
                      >
                        {batch.status}
                      </span>
                    </td>
                    <td className="px-3 py-4 text-right tabular-nums">
                      {batch.counts.rows_total.toLocaleString()}
                    </td>
                    <td className="px-3 py-4 text-right tabular-nums">
                      {batch.counts.errors.toLocaleString()}
                    </td>
                    <td className="px-3 py-4 text-right tabular-nums">
                      {batch.counts.warnings.toLocaleString()}
                    </td>
                    <td className="px-3 py-4 whitespace-nowrap text-slate-600">
                      {new Date(batch.created_at).toLocaleString()}
                    </td>
                    <td className="px-3 py-4">
                      <button
                        type="button"
                        onClick={() =>
                          setSelectedBatchId((current) =>
                            current === batch.id ? null : batch.id,
                          )
                        }
                        className="font-medium text-indigo-700 underline"
                        aria-expanded={selectedBatchId === batch.id}
                      >
                        {selectedBatchId === batch.id
                          ? "Hide issues"
                          : "View issues"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-500">
              Showing {offset + 1}–{offset + items.length} of {total}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={offset === 0 || batchesQuery.isFetching}
                onClick={() =>
                  setOffset((current) => Math.max(0, current - limit))
                }
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={offset + limit >= total || batchesQuery.isFetching}
                onClick={() => setOffset((current) => current + limit)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}

      {selectedBatchId && (
        <div className="space-y-3 rounded-lg border border-slate-200 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold text-slate-900">Validation issues</h3>
            <button
              type="button"
              onClick={() => setSelectedBatchId(null)}
              className="text-sm text-slate-600 underline"
            >
              Close
            </button>
          </div>

          {issuesQuery.isPending ? (
            <p className="text-sm text-slate-500">Loading issues…</p>
          ) : issuesQuery.isError ? (
            <div className="text-sm text-red-800">
              Could not load issues for this batch.
              <button
                type="button"
                onClick={() => void issuesQuery.refetch()}
                className="ml-2 underline"
              >
                Retry
              </button>
            </div>
          ) : issuesQuery.data.length === 0 ? (
            <p className="text-sm text-slate-500">
              The API returned no validation issues for this batch.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Row</th>
                    <th className="px-3 py-2">Severity</th>
                    <th className="px-3 py-2">Rule</th>
                    <th className="px-3 py-2">Message</th>
                    <th className="px-3 py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {issuesQuery.data.map((issue) => (
                    <tr key={issue.id} className="align-top">
                      <td className="px-3 py-3 tabular-nums">
                        {issue.row_number}
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={`rounded-full px-2 py-1 text-xs font-medium ${severityStyles[issue.severity]}`}
                        >
                          {issue.severity}
                        </span>
                      </td>
                      <td className="px-3 py-3 font-mono text-xs">
                        {issue.rule_code}
                      </td>
                      <td className="px-3 py-3">{issue.message}</td>
                      <td className="px-3 py-3">
                        {issue.resolved ? "Resolved" : "Open"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default function InstitutionPage() {
  const { role, institutionId } = useIdentity();
  const [search, setSearch] = useState("");
  const [overrunsOnly, setOverrunsOnly] = useState(false);
  const academicYear = "2026-27";
  const endpoint = `/institutions/${institutionId}/seat-ledger?academic_year=${academicYear}`;

  const query = useQuery({
    queryKey: ["seat-ledger", institutionId, role, academicYear],
    queryFn: () => api<SeatLedger>(endpoint),
    enabled: Boolean(institutionId),
  });

  const programmes = useMemo(
    () => query.data?.programmes ?? [],
    [query.data?.programmes],
  );

  const totals = useMemo(
    () =>
      programmes.reduce(
        (total, programme) => {
          total.approved += programme.approved_total;
          total.admitted += programme.admitted_total;
          total.available += programme.pools.reduce(
            (sum, pool) => sum + pool.available,
            0,
          );
          total.overruns += programme.overrun > 0 ? 1 : 0;
          return total;
        },
        { approved: 0, admitted: 0, available: 0, overruns: 0 },
      ),
    [programmes],
  );

  const filteredProgrammes = programmes.filter((programme) => {
    const term = search.trim().toLowerCase();
    const matchesSearch =
      programme.programme_code.toLowerCase().includes(term) ||
      programme.programme_name.toLowerCase().includes(term);

    return matchesSearch && (!overrunsOnly || programme.overrun > 0);
  });

  if (!institutionId) {
    return (
      <section className="rounded-xl border border-amber-200 bg-amber-50 p-5">
        <h1 className="text-xl font-semibold">Institution Dashboard</h1>
        <p className="mt-2 text-sm text-amber-900">
          No institution is associated with the current demo identity. Select an
          institution identity before viewing the seat ledger.
        </p>
      </section>
    );
  }

  if (query.isPending) {
    return (
      <section className="space-y-4">
        <h1 className="text-2xl font-semibold">Institution Dashboard</h1>
        <p className="text-sm text-slate-500">
          Loading seat ledger for {academicYear}…
        </p>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <div
              key={item}
              className="h-28 animate-pulse rounded-xl bg-slate-200"
            />
          ))}
        </div>
      </section>
    );
  }

  if (query.isError) {
    return (
      <section className="rounded-xl border border-red-200 bg-white p-6">
        <h1 className="text-xl font-semibold text-red-800">
          Could not load seat ledger
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Check the API connection and current demo identity.
        </p>
        <button
          type="button"
          onClick={() => void query.refetch()}
          className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700"
        >
          Retry
        </button>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-indigo-700">
            Institution Portal
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Seat Ledger
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Academic year {query.data?.academic_year ?? academicYear}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
        >
          {query.isFetching ? "Refreshing…" : "Refresh data"}
        </button>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="Approved seats"
          value={totals.approved}
          description="Across all returned programmes"
        />
        <Metric
          label="Admitted"
          value={totals.admitted}
          description="Reported admissions"
        />
        <Metric
          label="Available seats"
          value={totals.available}
          description="Sum of pool availability"
        />
        <Metric
          label="Programmes over limit"
          value={totals.overruns}
          description="Programmes with a positive overrun"
        />
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-4 border-b border-slate-200 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Programme breakdown</h2>
            <p className="mt-1 text-sm text-slate-500">
              {filteredProgrammes.length} of {programmes.length} programmes
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="sr-only" htmlFor="programme-search">
              Search programmes
            </label>
            <input
              id="programme-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search programmes…"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            />
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={overrunsOnly}
                onChange={(event) => setOverrunsOnly(event.target.checked)}
                className="rounded border-slate-300"
              />
              Overruns only
            </label>
          </div>
        </div>

        {programmes.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-500">
            No programme data was returned for this academic year.
          </p>
        ) : filteredProgrammes.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-500">
            No programmes match your filters.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-medium">Programme</th>
                  <th className="px-5 py-3 text-right font-medium">Approved</th>
                  <th className="px-5 py-3 text-right font-medium">Admitted</th>
                  <th className="px-5 py-3 text-right font-medium">
                    Available
                  </th>
                  <th className="px-5 py-3 text-right font-medium">Overrun</th>
                  <th className="px-5 py-3 font-medium">Pool breakdown</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredProgrammes.map((programme: ProgrammeLedger) => (
                  <tr
                    key={programme.programme_id}
                    className="align-top hover:bg-slate-50"
                  >
                    <td className="px-5 py-4">
                      <p className="font-medium text-slate-900">
                        {programme.programme_name}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {programme.programme_code}
                      </p>
                    </td>
                    <td className="px-5 py-4 text-right tabular-nums">
                      {programme.approved_total.toLocaleString()}
                    </td>
                    <td className="px-5 py-4 text-right tabular-nums">
                      {programme.admitted_total.toLocaleString()}
                    </td>
                    <td className="px-5 py-4 text-right tabular-nums">
                      {programme.pools
                        .reduce((sum, pool) => sum + pool.available, 0)
                        .toLocaleString()}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <span
                        className={
                          programme.overrun > 0
                            ? "rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700"
                            : "rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600"
                        }
                      >
                        {programme.overrun.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap gap-2">
                        {programme.pools.map((pool) => (
                          <span
                            key={pool.pool}
                            title={`Rule version: ${pool.rule_version}`}
                            className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600"
                          >
                            {poolLabels[pool.pool]}: {pool.admitted}/
                            {pool.approved_seats}
                          </span>
                        ))}
                        {programme.pools.length === 0 && (
                          <span className="text-xs text-slate-400">
                            No pool details
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="-mt-3 text-xs text-slate-400">
        Figures reflect the seat-ledger API response. Availability is summed
        from pool-level values; this page does not recalculate server rules.
      </p>

      <StudentRegistry
        institutionId={institutionId}
        academicYear={academicYear}
      />
      <UploadWizard institutionId={institutionId} />

      <BatchHistory institutionId={institutionId} />

      <PostLockEditRequests
        institutionId={institutionId}
        academicYear={academicYear}
      />
    </section>
  );
}
