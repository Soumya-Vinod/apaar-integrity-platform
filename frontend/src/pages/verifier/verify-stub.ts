// Owner: Dev X

export interface VerificationResult {
  valid: boolean
  reason?: string
  claims?: Record<string, unknown>
  expiresAt?: string
  offline: boolean
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (value.length % 4)) % 4)
  return atob(normalized)
}

// Temporary verifier; replace this implementation with lib/credential-verify.
export async function verifyCredential(qrText: string, publicKeyB64: string): Promise<VerificationResult> {
  void publicKeyB64
  try {
    const [encodedPayload, signature] = qrText.split('.')
    if (!encodedPayload || !signature) throw new Error('Invalid credential format')
    const payload: unknown = JSON.parse(decodeBase64Url(encodedPayload))
    if (typeof payload !== 'object' || payload === null) throw new Error('Invalid payload')
    const record = payload as { claims?: unknown; exp?: unknown }
    return {
      valid: true,
      offline: false,
      claims: typeof record.claims === 'object' && record.claims !== null
        ? record.claims as Record<string, unknown>
        : {},
      expiresAt: typeof record.exp === 'string' ? record.exp : undefined,
    }
  } catch {
    return { valid: false, reason: 'Not a valid credential QR', offline: false }
  }
}
