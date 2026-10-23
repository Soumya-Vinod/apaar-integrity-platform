// Owner: Dev X
import { Html5Qrcode } from 'html5-qrcode'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, api } from '../../lib/api'
import type { components } from '../../lib/api-types'
import { verifyCredential, type VerificationResult } from './verify-stub'

type PublicKey = components['schemas']['PublicKey']
type RevocationList = components['schemas']['RevocationList']

const CLAIM_LABELS: Record<string, string> = {
  institution: 'Institution',
  programme: 'Programme',
  academic_year: 'Academic year',
  status: 'Enrolment status',
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return `The verification service returned an error (${error.status}).`
  return 'We could not reach the verification service. Please try again.'
}

function formatDate(value: string | undefined): string {
  if (!value) return 'Unknown'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function decodePayload(qrText: string): Record<string, unknown> | null {
  try {
    const encoded = qrText.split('.')[0]
    const normalized = encoded.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (encoded.length % 4)) % 4)
    const payload: unknown = JSON.parse(atob(normalized))
    return typeof payload === 'object' && payload !== null ? payload as Record<string, unknown> : null
  } catch {
    return null
  }
}

function ResultCard({
  result,
  revoked,
  onReset,
}: {
  result: VerificationResult
  revoked: boolean
  onReset: () => void
}) {
  const expired = Boolean(result.expiresAt && new Date(result.expiresAt).getTime() < Date.now())
  const claims = result.claims ?? {}
  const displayedClaims = Object.entries(CLAIM_LABELS)
    .filter(([key]) => !key.includes('apaar') && claims[key] !== undefined && claims[key] !== null)

  let title = 'Verified'
  let titleClass = 'bg-emerald-100 text-emerald-800'
  let panelClass = 'border-emerald-200 bg-emerald-50'
  let reason = ''
  if (!result.valid) {
    title = 'Invalid signature'
    titleClass = 'bg-red-100 text-red-800'
    panelClass = 'border-red-200 bg-red-50'
    reason = result.reason ?? 'This credential could not be verified.'
  } else if (revoked) {
    title = 'Revoked'
    titleClass = 'bg-amber-100 text-amber-900'
    panelClass = 'border-amber-200 bg-amber-50'
    reason = 'This credential was revoked by the student.'
  } else if (expired) {
    title = 'Expired'
    titleClass = 'bg-amber-100 text-amber-900'
    panelClass = 'border-amber-200 bg-amber-50'
    reason = 'This credential is past its expiry time.'
  }

  return (
    <section className={`rounded-2xl border p-5 ${panelClass}`} aria-live="polite">
      <div className="flex items-center justify-between gap-3">
        <h2 className={`rounded-full px-3 py-1 text-lg font-bold ${titleClass}`}>{title}</h2>
        {result.offline && <span className="text-sm font-semibold text-slate-700">Checked offline</span>}
      </div>
      {reason && <p className="mt-4 text-base font-medium text-slate-800">{reason}</p>}
      {result.valid && !revoked && !expired && (
        <div className="mt-5 space-y-3">
          {displayedClaims.length > 0 ? (
            displayedClaims.map(([key, label]) => (
              <div key={key} className="rounded-xl bg-white/80 p-3">
                <dt className="text-sm font-semibold text-slate-500">{label}</dt>
                <dd className="mt-1 break-words text-lg text-slate-900">{String(claims[key])}</dd>
              </div>
            ))
          ) : (
            <p className="text-base text-slate-700">No shared facts were included.</p>
          )}
          <p className="pt-2 text-sm text-slate-700">Expires {formatDate(result.expiresAt)}</p>
        </div>
      )}
      <p className="mt-6 border-t border-slate-300/60 pt-4 text-sm text-slate-700">
        Verified with the institution&apos;s digital signature. No student data was looked up.
      </p>
      <button
        type="button"
        onClick={onReset}
        className="mt-5 w-full rounded-xl bg-slate-900 px-4 py-3 text-base font-bold text-white hover:bg-slate-700"
      >
        Verify another
      </button>
    </section>
  )
}

export default function VerifierPage() {
  const scannerRef = useRef<Html5Qrcode | null>(null)
  const scannerActiveRef = useRef(false)
  const [cameraMessage, setCameraMessage] = useState<string | null>(null)
  const [qrText, setQrText] = useState('')
  const [result, setResult] = useState<VerificationResult | null>(null)
  const [revoked, setRevoked] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function stopScanner() {
    scannerActiveRef.current = false
    const scanner = scannerRef.current
    scannerRef.current = null
    if (!scanner) return
    try {
      await scanner.stop()
      scanner.clear()
    } catch {
      // The camera may already have stopped after a permission or device error.
    }
  }

  useEffect(() => {
    const scanner = new Html5Qrcode('verifier-qr-reader')
    scannerRef.current = scanner
    scannerActiveRef.current = true
    scanner
      .start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
          if (!scannerActiveRef.current) return
          setQrText(decodedText)
          void stopScanner()
        },
        () => undefined,
      )
      .catch(() => {
        scannerActiveRef.current = false
        setCameraMessage('Camera access is unavailable. You can still paste the QR text below.')
      })
    return () => {
      void stopScanner()
    }
  }, [])

  async function handleVerify(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault()
    const text = qrText.trim()
    if (!text) {
      setError('Paste the QR text or scan a credential before verifying.')
      return
    }
    setChecking(true)
    setError(null)
    setResult(null)
    setRevoked(false)
    try {
      const [publicKey, revocations] = await Promise.all([
        api<PublicKey>('/credentials/public-key'),
        api<RevocationList>('/credentials/revocations'),
      ])
      const verification = await verifyCredential(text, publicKey.public_key_b64)
      const payload = decodePayload(text)
      const credentialId = typeof payload?.cid === 'string' ? payload.cid : null
      setRevoked(Boolean(credentialId && revocations.revoked.some((item) => item.credential_id === credentialId)))
      setResult(verification)
    } catch (verificationError) {
      setError(getErrorMessage(verificationError))
    } finally {
      setChecking(false)
    }
  }

  function reset() {
    setResult(null)
    setRevoked(false)
    setError(null)
    setQrText('')
    setCameraMessage(null)
  }

  if (result) {
    return (
      <section className="mx-auto max-w-lg space-y-5">
        <h1 className="text-3xl font-bold text-slate-900">Credential result</h1>
        <ResultCard result={result} revoked={revoked} onReset={reset} />
      </section>
    )
  }

  return (
    <section className="mx-auto max-w-lg space-y-6">
      <div>
        <p className="text-sm font-bold uppercase tracking-wide text-blue-700">Verifier</p>
        <h1 className="mt-1 text-3xl font-bold text-slate-900">Check a credential</h1>
        <p className="mt-2 text-base text-slate-600">Scan the student&apos;s QR code or paste its text.</p>
      </div>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white p-3">
        <div id="verifier-qr-reader" className="min-h-16" />
        {cameraMessage && <p className="p-3 text-base text-slate-600">{cameraMessage}</p>}
      </div>
      <form onSubmit={handleVerify} className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4">
        <label htmlFor="qr-text" className="text-base font-bold text-slate-900">
          Paste QR text
        </label>
        <textarea
          id="qr-text"
          value={qrText}
          onChange={(event) => setQrText(event.target.value)}
          rows={5}
          placeholder="Paste the credential QR text here"
          className="w-full resize-y rounded-xl border border-slate-300 p-3 font-mono text-sm outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
        />
        {error && <p role="alert" className="text-base text-red-700">{error}</p>}
        <button
          type="submit"
          disabled={checking || !qrText.trim()}
          className="w-full rounded-xl bg-blue-700 px-4 py-3 text-base font-bold text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {checking ? 'Checking…' : 'Verify'}
        </button>
      </form>
    </section>
  )
}
