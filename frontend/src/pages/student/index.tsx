// Owner: Dev E
import { useState, type FormEvent } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { ApiError, api } from '../../lib/api'
import type { components } from '../../lib/api-types'

type Credential = components['schemas']['Credential']
type CredentialRequest = components['schemas']['CredentialRequest']
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

function ShareCredential() {
  const [recipient, setRecipient] = useState('')
  const [expiry, setExpiry] = useState('1d')
  const [fields, setFields] = useState<SharedField[]>([])
  const [credential, setCredential] = useState<Credential | null>(null)
  const [revoked, setRevoked] = useState(false)
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
      setCredential(created)
      setRevoked(false)
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
      setRevoked(true)
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
  const [activeTab, setActiveTab] = useState('share')
  const tabs = [
    { id: 'records', label: 'My records' },
    { id: 'share', label: 'Share a credential' },
    { id: 'consents', label: 'Consents' },
    { id: 'viewed', label: 'Who viewed my record' },
  ]

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
      {activeTab === 'share' ? <ShareCredential /> : <Placeholder title={tabs.find((tab) => tab.id === activeTab)?.label ?? ''} />}
    </section>
  )
}
