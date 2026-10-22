// Owner: Dev D
// Demo identity kept in localStorage and sent as X-Demo-Role / X-Demo-Institution in mock mode.
import { useSyncExternalStore } from 'react'

export const ROLES = [
  'institution_admin',
  'institution_operator',
  'aicte_admin',
  'student',
  'verifier',
  'auditor',
] as const

export type Role = (typeof ROLES)[number]

export interface DemoIdentity {
  role: Role
  institutionId: string
}

// Shadow Institute of Technology in the backend mock fixtures.
export const DEFAULT_INSTITUTION_ID = '10000000-0000-4000-8000-000000000003'
const STORAGE_KEY = 'apaar-demo-identity'
const DEFAULT_IDENTITY: DemoIdentity = { role: 'aicte_admin', institutionId: DEFAULT_INSTITUTION_ID }

function read(): DemoIdentity {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_IDENTITY
    const parsed = JSON.parse(raw) as Partial<DemoIdentity>
    const role = ROLES.includes(parsed.role as Role) ? (parsed.role as Role) : DEFAULT_IDENTITY.role
    return { role, institutionId: parsed.institutionId || DEFAULT_INSTITUTION_ID }
  } catch {
    return DEFAULT_IDENTITY
  }
}

let current = read()
const listeners = new Set<() => void>()

export function getIdentity(): DemoIdentity {
  return current
}

export function setIdentity(next: Partial<DemoIdentity>): void {
  current = { ...current, ...next }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(current))
  } catch {
    // Storage unavailable (private mode, blocked): keep the in-memory value.
  }
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useIdentity(): DemoIdentity {
  return useSyncExternalStore(subscribe, getIdentity)
}
