// Owner: Dev E
import { useEffect, useState, type FormEvent } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { ApiError, api } from '../../lib/api'
import type { components } from '../../lib/api-types'

type Credential = components['schemas']['Credential']
type CredentialRequest = components['schemas']['CredentialRequest']
type Admission = components['schemas']['Admission']
type StudentRecords = components['schemas']['StudentRecords']
type StudentResponseResult = components['schemas']['StudentResponseResult']
type AccessLogEntry = components['schemas']['AccessLogEntry']
type Consent = components['schemas']['Consent']
type ConsentCreate = components['schemas']['ConsentCreate']
type SharedField = 'status' | 'institution' | 'programme' | 'academic_year'

const SHARED_FIELDS: { id: SharedField; label: string }[] = [
  { id: 'status', label: 'Enrolment status' },
  { id: 'institution', label: 'Institution' },
  { id: 'programme', label: 'Programme' },
  { id: 'academic_year', label: 'Academic year' },
]

const EXPIRY_OPTIONS = [
  { label: '15 minutes (coming soon)', value: '15m', expiresInDays: 1, disabled: true },
  { label: '1 day', value: '1d', expiresInDays: 1 },
  { label: '7 days', value: '7d', expiresInDays: 7 },
]

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.body === 'object' && error.body !== null && 'detail' in error.body) {
      const detail = (error.body as { detail?: unknown }).detail
      if (typeof detail === 'string') return detail
    }
    return `The request failed (${error.status}). Please try again.`
  }
  return 'We could not reach the service. Check that the backend is running and try again.'
}

function formatExpiry(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function Placeholder({ title }: { title: string }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 text-center">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <p className="mt-2 text-sm text-slate-500">Coming soon</p>
    </section>
  )
}

const STATUS_DETAILS: Record<
  Admission['status'],
  { label: string; className: string }
> = {
  submitted: { label: 'Submitted', className: 'bg-blue-100 text-blue-800' },
  student_confirmed: { label: 'Confirmed', className: 'bg-emerald-100 text-emerald-800' },
  student_disputed: { label: 'Disputed', className: 'bg-red-100 text-red-800' },
  no_response: { label: 'No response', className: 'bg-slate-100 text-slate-700' },
  withdrawn: { label: 'Withdrawn', className: 'bg-slate-100 text-slate-700' },
}

function RecordsLoading() {
  return (
    <div className="space-y-3" aria-label="Loading records">
      {[1, 2].map((item) => (
        <div key={item} className="h-40 animate-pulse rounded-xl bg-slate-200" />
      ))}
    </div>
  )
}

function formatAccessedAt(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      })
}

function viewerTypeLabel(role: string): string | null {
  const normalized = role.toLowerCase()
  if (normalized.includes('verifier')) return 'Verifier'
  if (normalized.includes('institution')) return 'Institution'
  if (normalized.includes('aicte') || normalized.includes('auditor')) return 'AICTE'
  return null
}

function AccessLogLoading() {
  return (
    <div className="space-y-3" aria-label="Loading access history">
      {[1, 2, 3].map((item) => (
        <div key={item} className="h-20 animate-pulse rounded-xl bg-slate-200" />
      ))}
    </div>
  )
}

function AccessLogEntryContent({ entry }: { entry: AccessLogEntry }) {
  const viewerType = viewerTypeLabel(entry.accessor_role)
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="font-semibold text-slate-900">{entry.accessor}</span>
      {viewerType && (
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
          {viewerType}
        </span>
      )}
    </div>
  )
}

function AccessLog() {
  const [entries, setEntries] = useState<AccessLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadAccessLog() {
    setLoading(true)
    setError(null)
    try {
      const response = await api<AccessLogEntry[]>('/students/me/access-log')
      setEntries(
        [...response].sort(
          (left, right) =>
            new Date(right.accessed_at).getTime() - new Date(left.accessed_at).getTime(),
        ),
      )
    } catch (loadError) {
      setError(
        loadError instanceof ApiError
          ? `We could not load your access history (${loadError.status}).`
          : 'We could not reach your access history. Please try again.',
      )
    } finally {
      setLoading(false)
    }

  }

  useEffect(() => {
    void loadAccessLog()
  }, [])

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Who viewed my record</h2>
        <p className="mt-1 text-sm text-slate-600">See when your record was accessed and why.</p>
      </div>
      {loading && <AccessLogLoading />}
      {!loading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <p className="text-sm text-red-800">{error}</p>
          <button
            type="button"
            onClick={() => void loadAccessLog()}
            className="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800"
          >
            Retry
          </button>
        </div>
      )}
      {!loading && !error && entries.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-600">
          No one has viewed your record yet.
        </div>
      )}
      {!loading && !error && entries.length > 0 && (
        <>
          <div className="hidden overflow-hidden rounded-xl border border-slate-200 bg-white md:block">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-semibold">Who</th>
                  <th className="px-5 py-3 font-semibold">Purpose</th>
                  <th className="px-5 py-3 font-semibold">Date and time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td className="px-5 py-4"><AccessLogEntryContent entry={entry} /></td>
                    <td className="px-5 py-4 text-sm text-slate-700">{entry.purpose}</td>
                    <td className="px-5 py-4">
                      <time dateTime={entry.accessed_at}>{formatAccessedAt(entry.accessed_at)}</time>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="space-y-3 md:hidden">
            {entries.map((entry) => (
              <article key={entry.id} className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Who</p>
                  <AccessLogEntryContent entry={entry} />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Purpose</p>
                  <p className="mt-1 text-sm text-slate-700">{entry.purpose}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Date and time</p>
                  <time dateTime={entry.accessed_at} className="mt-1 block text-sm text-slate-600">
                    {formatAccessedAt(entry.accessed_at)}
                  </time>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  )
}

function formatConsentDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      })
}

function ConsentsLoading() {
  return (
    <div className="space-y-3" aria-label="Loading consents">
      {[1, 2].map((item) => <div key={item} className="h-28 animate-pulse rounded-xl bg-slate-200" />)}
    </div>
  )
}

interface ConsentsState {
  consents: Consent[]
  loading: boolean
  error: string | null
  onRetry: () => void
  onConsentChange: (consentId: string, updated: Consent, wasGranted: boolean) => void
}

function Consents({ consents, loading, error, onRetry, onConsentChange }: ConsentsState) {
  const [savingId, setSavingId] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  useEffect(() => {
    if (!toast) return
    const timeout = window.setTimeout(() => setToast(null), 3500)
    return () => window.clearTimeout(timeout)
  }, [toast])

  async function toggleConsent(consent: Consent) {
    const granted = !consent.revoked_at
    setSavingId(consent.id)
    setToast(null)
    const request: ConsentCreate = {
      verifier_id: consent.verifier_id,
      purpose: consent.purpose,
      fields: consent.fields,
      expires_in_days: 30,
    }
    try {
      const updated = await api<Consent>('/students/me/consents', {
        method: 'POST',
        body: JSON.stringify(request),
      })
      onConsentChange(consent.id, updated, granted)
      setToast(granted ? 'Consent withdrawn.' : 'Consent granted.')
    } catch (saveError) {
      setToast(saveError instanceof ApiError
        ? `We could not update this consent (${saveError.status}).`
        : 'We could not update this consent. Please try again.')
    } finally {
      setSavingId(null)
    }
  }

  function requestOptOut() {
    if (window.confirm('Opt out of APAAR-based sharing?')) setToast('Coming soon')
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Consents</h2>
        <p className="mt-1 text-sm text-slate-600">Control who can use your shared record.</p>
      </div>
      {toast && <div role="status" className="rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white">{toast}</div>}
      <div className="rounded-xl border-2 border-amber-200 bg-amber-50 p-4 sm:p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="font-semibold text-slate-900">Opt out of APAAR-based sharing</h3>
            <p className="mt-2 text-sm text-slate-700">
              The Supreme Court (July 2026) requires that you can explicitly opt out of APAAR-based sharing.
            </p>
          </div>
          <button type="button" onClick={requestOptOut} className="shrink-0 rounded-full bg-slate-300 px-3 py-1 text-xs font-bold text-slate-700 hover:bg-slate-400">
            Opt out
          </button>
        </div>
      </div>
      {loading && <ConsentsLoading />}
      {!loading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <p className="text-sm text-red-800">{error}</p>
          <button type="button" onClick={onRetry} className="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800">Retry</button>
        </div>
      )}
      {!loading && !error && consents.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-600">No consents recorded yet.</div>
      )}
      {!loading && !error && consents.length > 0 && (
        <div className="space-y-3">
          {consents.map((consent) => {
            const granted = !consent.revoked_at
            const saving = savingId === consent.id
            return (
              <article key={consent.id} className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className="font-semibold text-slate-900">{consent.purpose}</h3>
                    <p className="mt-1 text-sm text-slate-500">
                      {granted ? `Granted ${formatConsentDate(consent.granted_at)}` : `Withdrawn ${formatConsentDate(consent.revoked_at ?? consent.granted_at)}`}
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={granted}
                    aria-label={`${granted ? 'Withdraw' : 'Grant'} consent for ${consent.purpose}`}
                    disabled={saving}
                    onClick={() => void toggleConsent(consent)}
                    className={`relative h-7 w-12 shrink-0 rounded-full transition ${granted ? 'bg-emerald-600' : 'bg-slate-300'} disabled:cursor-not-allowed disabled:opacity-60`}
                  >
                    <span className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition ${granted ? 'left-6' : 'left-1'}`} />
                  </button>
                </div>
                <span className={`mt-3 inline-block rounded-full px-2.5 py-1 text-xs font-bold ${granted ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}`}>
                  {saving ? 'Saving…' : granted ? 'Granted' : 'Withdrawn'}
                </span>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

interface RecordsState {
  records: StudentRecords | null
  loading: boolean
  error: string | null
  onRetry: () => void
  onStatusChange: (admissionId: string, status: Admission['status']) => void
}

function MyRecords({ records, loading, error, onRetry, onStatusChange }: RecordsState) {
  const [respondingId, setRespondingId] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    if (!toast) return
    const timeout = window.setTimeout(() => setToast(null), 3500)
    return () => window.clearTimeout(timeout)
  }, [toast])

  async function respondToAdmission(admission: Admission, response: 'confirmed' | 'disputed') {
    if (response === 'disputed' && !window.confirm('This will open an investigation at AICTE. Continue?')) {
      return
    }

    setRespondingId(admission.id)
    setToast(null)
    try {
      const result = await api<StudentResponseResult>(
        `/students/me/admissions/${encodeURIComponent(admission.id)}/response`,
        { method: 'POST', body: JSON.stringify({ response }) },
      )
      setToast(response === 'confirmed' ? 'Your record was confirmed.' : 'Report sent to AICTE.')
      onStatusChange(admission.id, result.status)
    } catch (responseError) {
      if (responseError instanceof ApiError && responseError.status === 404) {
        setToast('Coming soon')
      } else {
        setToast(
          responseError instanceof ApiError
            ? `We could not update this record (${responseError.status}).`
            : 'We could not update this record. Please try again.',
        )
      }
    } finally {
      setRespondingId(null)
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">My records</h2>
        <p className="mt-1 text-sm text-slate-600">Review the admission records linked to you.</p>
      </div>
      {toast && (
        <div role="status" className="rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white">
          {toast}
        </div>
      )}
      {loading && <RecordsLoading />}
      {!loading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5">
          <p className="text-sm text-red-800">{error}</p>
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800"
          >
            Retry
          </button>
        </div>
      )}
      {!loading && !error && records?.admissions.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-600">
          No admission records found.
        </div>
      )}
      {!loading && !error && records && records.admissions.length > 0 && (
        <div className="space-y-4">
          {records.admissions.map((admission) => {
            const status = STATUS_DETAILS[admission.status]
            const responding = respondingId === admission.id
            return (
              <article key={admission.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Admission record</p>
                    <h3 className="mt-1 text-lg font-semibold text-slate-900">{admission.institution_id}</h3>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-bold ${status.className}`}>
                    {status.label}
                  </span>
                </div>
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-slate-500">Programme</dt>
                    <dd className="mt-1 font-medium text-slate-900">{admission.programme_code || admission.programme_id}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Academic year</dt>
                    <dd className="mt-1 font-medium text-slate-900">{admission.academic_year}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">APAAR number</dt>
                    <dd className="mt-1 font-medium text-slate-900">{admission.apaar_id_masked ?? 'Not available'}</dd>
                  </div>
                </dl>
                {admission.status === 'submitted' && (
                  <div className="mt-5 flex flex-col gap-2 sm:flex-row">
                    <button
                      type="button"
                      disabled={responding}
                      onClick={() => void respondToAdmission(admission, 'confirmed')}
                      className="rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {responding ? 'Saving…' : 'Yes, this is me'}
                    </button>
                    <button
                      type="button"
                      disabled={responding}
                      onClick={() => void respondToAdmission(admission, 'disputed')}
                      className="rounded-lg border border-red-300 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {responding ? 'Saving…' : "This isn't me"}
                    </button>
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

interface ShareCredentialState {
  credential: Credential | null
  revoked: boolean
  onCredentialCreated: (credential: Credential) => void
  onRevoked: () => void
}

function ShareCredential({ credential, revoked, onCredentialCreated, onRevoked }: ShareCredentialState) {
  const [recipient, setRecipient] = useState('')
  const [expiry, setExpiry] = useState('1d')
  const [fields, setFields] = useState<SharedField[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRevoking, setIsRevoking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  function toggleField(field: SharedField) {
    setFields((current) =>
      current.includes(field) ? current.filter((item) => item !== field) : [...current, field],
    )
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const selectedExpiry = EXPIRY_OPTIONS.find((option) => option.value === expiry)
    if (!selectedExpiry || fields.length === 0 || !recipient.trim()) return

    const request: CredentialRequest = {
      verifier_id: recipient.trim(),
      purpose: 'Credential sharing',
      fields,
      expires_in_days: selectedExpiry.expiresInDays,
    }

    setError(null)
    setCopied(false)
    setIsSubmitting(true)
    try {
      const created = await api<Credential>('/credentials', {
        method: 'POST',
        body: JSON.stringify(request),
      })
      onCredentialCreated(created)
    } catch (submissionError) {
      setError(errorMessage(submissionError))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRevoke() {
    if (!credential) return
    setError(null)
    setIsRevoking(true)
    try {
      await api(`/credentials/${encodeURIComponent(credential.credential_id)}/revoke`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'Revoked by student' }),
      })
      onRevoked()
    } catch (revokeError) {
      setError(errorMessage(revokeError))
    } finally {
      setIsRevoking(false)
    }
  }

  async function copyQrText() {
    if (!credential) return
    try {
      await navigator.clipboard.writeText(credential.qr_payload)
      setCopied(true)
      setError(null)
    } catch {
      setError('We could not copy the QR text. Select it and copy it manually.')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Share a credential</h2>
        <p className="mt-1 text-sm text-slate-600">
          Choose the minimum facts needed for the person or organisation you are sharing with.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
        <fieldset>
          <legend className="text-sm font-semibold text-slate-900">Facts to share</legend>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {SHARED_FIELDS.map((field) => (
              <label key={field.id} className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 text-sm">
                <input
                  type="checkbox"
                  checked={fields.includes(field.id)}
                  onChange={() => toggleField(field.id)}
                  className="h-4 w-4 accent-blue-600"
                />
                <span>{field.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="grid gap-5 sm:grid-cols-2">
          <label className="text-sm font-semibold text-slate-900">
            Who is this for?
            <input
              type="text"
              value={recipient}
              onChange={(event) => setRecipient(event.target.value)}
              placeholder="e.g. Infosys HR"
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
              required
            />
          </label>
          <label className="text-sm font-semibold text-slate-900">
            Expires in
            <select
              value={expiry}
              onChange={(event) => setExpiry(event.target.value)}
              className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
            >
              {EXPIRY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value} disabled={option.disabled}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && (
          <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting || fields.length === 0 || !recipient.trim()}
          className="w-full rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-300 sm:w-auto"
        >
          {isSubmitting ? 'Creating credential…' : 'Create shareable credential'}
        </button>
      </form>

      {credential && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Credential ready</h2>
              <p className="mt-1 text-sm text-slate-600">
                Expires {formatExpiry(credential.expires_at)}
              </p>
            </div>
            {revoked ? (
              <span className="rounded-full bg-red-100 px-3 py-1 text-sm font-semibold text-red-800">Revoked</span>
            ) : (
              <button
                type="button"
                onClick={handleRevoke}
                disabled={isRevoking}
                className="rounded-lg border border-red-300 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isRevoking ? 'Revoking…' : 'Revoke'}
              </button>
            )}
          </div>
          <div className="mt-6 flex flex-col items-center">
            <div className={`rounded-xl border border-slate-200 bg-white p-4 ${revoked ? 'opacity-40' : ''}`}>
              <QRCodeSVG value={credential.qr_payload} size={220} includeMargin />
            </div>
            <p className="mt-4 max-w-md text-center text-sm text-slate-600">
              Your APAAR number is not inside this QR. Only the facts you ticked are shared.
            </p>
          </div>
          <div className="mt-6">
            <label htmlFor="qr-text" className="text-sm font-semibold text-slate-900">
              Raw QR text
            </label>
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <textarea
                id="qr-text"
                readOnly
                value={credential.qr_payload}
                rows={3}
                className="min-w-0 flex-1 resize-y rounded-lg border border-slate-300 bg-slate-50 p-3 font-mono text-xs text-slate-700"
              />
              <button
                type="button"
                onClick={copyQrText}
                className="self-start rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

export default function StudentPage() {
  const [activeTab, setActiveTab] = useState('records')
  const [records, setRecords] = useState<StudentRecords | null>(null)
  const [recordsLoading, setRecordsLoading] = useState(true)
  const [recordsError, setRecordsError] = useState<string | null>(null)
  const [consents, setConsents] = useState<Consent[]>([])
  const [consentsLoading, setConsentsLoading] = useState(true)
  const [consentsError, setConsentsError] = useState<string | null>(null)
  const [credential, setCredential] = useState<Credential | null>(null)
  const [credentialRevoked, setCredentialRevoked] = useState(false)
  const tabs = [
    { id: 'records', label: 'My records' },
    { id: 'share', label: 'Share a credential' },
    { id: 'consents', label: 'Consents' },
    { id: 'viewed', label: 'Who viewed my record' },
  ]

  async function loadRecords() {
    setRecordsLoading(true)
    setRecordsError(null)
    try {
      setRecords(await api<StudentRecords>('/students/me/records'))
    } catch (loadError) {
      setRecordsError(
        loadError instanceof ApiError
          ? `We could not load your records (${loadError.status}).`
          : 'We could not reach your records. Please try again.',
      )
    } finally {
      setRecordsLoading(false)
    }
  }

  async function loadConsents() {
    setConsentsLoading(true)
    setConsentsError(null)
    try {
      setConsents(await api<Consent[]>('/students/me/consents'))
    } catch (loadError) {
      setConsentsError(
        loadError instanceof ApiError
          ? `We could not load your consents (${loadError.status}).`
          : 'We could not reach your consents. Please try again.',
      )
    } finally {
      setConsentsLoading(false)
    }
  }

  useEffect(() => {
    void loadRecords()
    void loadConsents()
  }, [])

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Student portal</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Your records, your control</h1>
      </div>
      <div className="overflow-x-auto border-b border-slate-200">
        <div className="flex min-w-max gap-6" role="tablist" aria-label="Student portal sections">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`border-b-2 px-1 pb-3 text-sm font-semibold ${
                activeTab === tab.id
                  ? 'border-blue-700 text-blue-700'
                  : 'border-transparent text-slate-500 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      {activeTab === 'records' ? (
        <MyRecords
          records={records}
          loading={recordsLoading}
          error={recordsError}
          onRetry={() => void loadRecords()}
          onStatusChange={(admissionId, status) => {
            setRecords((current) => current
              ? {
                  ...current,
                  admissions: current.admissions.map((item) =>
                    item.id === admissionId ? { ...item, status } : item,
                  ),
                }
              : current)
          }}
        />
      ) : activeTab === 'share' ? (
        <ShareCredential
          credential={credential}
          revoked={credentialRevoked}
          onCredentialCreated={(created) => {
            setCredential(created)
            setCredentialRevoked(false)
          }}
          onRevoked={() => setCredentialRevoked(true)}
        />
      ) : activeTab === 'viewed' ? (
        <AccessLog />
      ) : activeTab === 'consents' ? (
        <Consents
          consents={consents}
          loading={consentsLoading}
          error={consentsError}
          onRetry={() => void loadConsents()}
          onConsentChange={(consentId, updated, wasGranted) => {
            setConsents((current) => current.map((item) => item.id === consentId
              ? {
                  ...updated,
                  id: consentId,
                  revoked_at: wasGranted ? new Date().toISOString() : updated.revoked_at,
                }
              : item))
          }}
        />
      ) : (
        <Placeholder title={tabs.find((tab) => tab.id === activeTab)?.label ?? ''} />
      )}
    </section>
  )
}
