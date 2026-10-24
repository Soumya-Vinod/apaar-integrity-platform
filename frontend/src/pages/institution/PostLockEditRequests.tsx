
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "../../lib/api-types";
import { api } from "../../lib/api";

type Admission = components["schemas"]["Admission"];
type EditRequest = components["schemas"]["EditRequest"];
type EditRequestCreate = components["schemas"]["EditRequestCreate"];

const fields = [
  { value: "admission_date", label: "Admission date" },
  { value: "admission_mode", label: "Admission mode" },
  { value: "qualifying_exam_pct", label: "Qualifying exam percentage" },
  { value: "student_name", label: "Student name" },
  { value: "dob", label: "Date of birth" },
  { value: "withdrawal", label: "Withdrawal" },
] as const;

const statusStyles: Record<EditRequest["status"], string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
};

interface Props {
  institutionId: string;
  academicYear: string;
}

export default function PostLockEditRequests({
  institutionId,
  academicYear,
}: Props) {
  const queryClient = useQueryClient();

  const [admissionId, setAdmissionId] = useState("");
  const [field, setField] =
    useState<(typeof fields)[number]["value"]>("admission_date");
  const [newValue, setNewValue] = useState("");
  const [reason, setReason] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const admissionsQuery = useQuery({
    queryKey: ["edit-request-admissions", institutionId, academicYear],
    queryFn: () => {
      const params = new URLSearchParams({
        institution_id: institutionId,
        academic_year: academicYear,
        limit: "100",
        offset: "0",
      });
      return api<Admission[]>(`/admissions?${params.toString()}`);
    },
    enabled: Boolean(institutionId),
  });

  const requestsQuery = useQuery({
    queryKey: [
      "institution-edit-requests",
      institutionId,
      academicYear,
      statusFilter,
    ],
    queryFn: () => {
      const params = new URLSearchParams({
        institution_id: institutionId,
        academic_year: academicYear,
        limit: "100",
        offset: "0",
      });

      if (statusFilter) params.set("status", statusFilter);

      return api<EditRequest[]>(`/edit-requests?${params.toString()}`);
    },
    enabled: Boolean(institutionId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: {
      admissionId: string;
      body: EditRequestCreate;
    }) =>
      api<EditRequest>(
        `/admissions/${payload.admissionId}/edit-requests`,
        {
          method: "POST",
          body: JSON.stringify(payload.body),
        },
      ),
    onSuccess: async () => {
      setNewValue("");
      setReason("");
      await queryClient.invalidateQueries({
        queryKey: ["institution-edit-requests", institutionId],
      });
    },
  });

  const admissions = admissionsQuery.data ?? [];
  const requests = requestsQuery.data ?? [];

  function submitRequest(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!admissionId || !newValue.trim() || !reason.trim()) return;

    createMutation.mutate({
      admissionId,
      body: {
        field,
        new_value: field === "withdrawal" ? "withdrawn" : newValue.trim(),
        reason: reason.trim(),
      },
    });
  }

  return (
    <section className="space-y-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">
          Post-lock Edit Requests
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Submit admission corrections for review after the submission window
          closes or locks. Requests require AICTE approval before changes are
          applied.
        </p>
      </div>

      <form
        onSubmit={submitRequest}
        className="space-y-4 rounded-lg border border-slate-200 p-4"
      >
        <h3 className="font-medium text-slate-900">Request an admission change</h3>

        {admissionsQuery.isError ? (
          <p className="text-sm text-red-700">
            Could not load admissions. Refresh the page and try again.
          </p>
        ) : (
          <label className="block space-y-1">
            <span className="text-sm font-medium text-slate-700">
              Student admission
            </span>
            <select
              required
              value={admissionId}
              onChange={(event) => setAdmissionId(event.target.value)}
              disabled={admissionsQuery.isPending || admissions.length === 0}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">
                {admissionsQuery.isPending
                  ? "Loading admissions…"
                  : admissions.length === 0
                    ? "No admissions available"
                    : "Select a student"}
              </option>
              {admissions.map((admission) => (
                <option key={admission.id} value={admission.id}>
                  {admission.student_name} — {admission.programme_code}
                  {admission.apaar_id_masked
                    ? ` — ${admission.apaar_id_masked}`
                    : ""}
                </option>
              ))}
            </select>
            <span className="text-xs text-slate-500">
              APAAR identifiers are shown only in masked form.
            </span>
          </label>
        )}

        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">
            Field to change
          </span>
          <select
            value={field}
            onChange={(event) => {
              setField(event.target.value as (typeof fields)[number]["value"]);
              setNewValue("");
            }}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            {fields.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        {field === "withdrawal" ? (
          <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
            This requests withdrawal of the admission. If approved, the
            backend will process the withdrawal and release the seat.
          </p>
        ) : (
          <label className="block space-y-1">
            <span className="text-sm font-medium text-slate-700">
              Proposed value
            </span>
            <input
              required
              value={newValue}
              onChange={(event) => setNewValue(event.target.value)}
              type={
                field === "admission_date" || field === "dob"
                  ? "date"
                  : field === "qualifying_exam_pct"
                    ? "number"
                    : "text"
              }
              min={field === "qualifying_exam_pct" ? 0 : undefined}
              max={field === "qualifying_exam_pct" ? 100 : undefined}
              step={field === "qualifying_exam_pct" ? "any" : undefined}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Enter the corrected value"
            />
          </label>
        )}

        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">
            Reason for request
          </span>
          <textarea
            required
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            rows={3}
            maxLength={1000}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Explain why this correction is needed…"
          />
        </label>

        {createMutation.isError && (
          <p role="alert" className="text-sm text-red-700">
            Request failed. The submission window may not be locked, or the
            server may have rejected the request. Check the API response and
            try again if appropriate.
          </p>
        )}

        {createMutation.isSuccess && (
          <p role="status" className="text-sm text-emerald-700">
            Edit request submitted successfully.
          </p>
        )}

        <button
          type="submit"
          disabled={
            createMutation.isPending ||
            !admissionId ||
            !reason.trim() ||
            (field !== "withdrawal" && !newValue.trim())
          }
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {createMutation.isPending ? "Submitting…" : "Submit edit request"}
        </button>
      </form>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-medium text-slate-900">Request history</h3>
            <p className="text-sm text-slate-500">
              Requests for academic year {academicYear}.
            </p>
          </div>

          <div className="flex gap-2">
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              aria-label="Filter edit requests by status"
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>

            <button
              type="button"
              onClick={() => void requestsQuery.refetch()}
              disabled={requestsQuery.isFetching}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
            >
              {requestsQuery.isFetching ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </div>

        {requestsQuery.isPending ? (
          <p className="py-5 text-sm text-slate-500">
            Loading edit requests…
          </p>
        ) : requestsQuery.isError ? (
          <div className="rounded-lg bg-red-50 p-4 text-sm text-red-800">
            Could not load edit requests.
            <button
              type="button"
              onClick={() => void requestsQuery.refetch()}
              className="ml-2 underline"
            >
              Retry
            </button>
          </div>
        ) : requests.length === 0 ? (
          <p className="rounded-lg bg-slate-50 p-6 text-center text-sm text-slate-500">
            No edit requests found.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-3">Student</th>
                  <th className="px-3 py-3">Field</th>
                  <th className="px-3 py-3">Proposed value</th>
                  <th className="px-3 py-3">Reason</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Requested</th>
                  <th className="px-3 py-3">Decision note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {requests.map((request) => (
                  <tr key={request.id} className="align-top hover:bg-slate-50">
                    <td className="px-3 py-3">
                      <p className="font-medium text-slate-900">
                        {request.admission?.student_name ?? "Admission"}
                      </p>
                      <p className="mt-1 font-mono text-xs text-slate-500">
                        {request.admission?.apaar_id_masked ?? ""}
                      </p>
                    </td>
                    <td className="px-3 py-3">
                      {fields.find((item) => item.value === request.field)
                        ?.label ?? request.field}
                    </td>
                    <td className="px-3 py-3">{request.new_value}</td>
                    <td className="max-w-64 whitespace-normal px-3 py-3">
                      {request.reason}
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`whitespace-nowrap rounded-full px-2 py-1 text-xs font-medium ${statusStyles[request.status]}`}
                      >
                        {request.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-slate-600">
                      {new Date(request.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-3">
                      {request.decision_note || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
