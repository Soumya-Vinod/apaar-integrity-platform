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

// ------------------------------------------------------------------ routes per role
export interface RouteAccess {
  path: string
  label: string
  roles: readonly Role[]
  /** Who the view is for, as in "This view is for …". */
  audience: string
}

// Same allow list as the header nav. The first role is the one offered by "Switch to …".
export const ROUTES: readonly RouteAccess[] = [
  { path: '/', label: 'Home', roles: ROLES, audience: 'everyone' },
  {
    path: '/institution',
    label: 'Institution',
    roles: ['institution_admin', 'institution_operator'],
    audience: 'institution staff',
  },
  { path: '/aicte', label: 'AICTE', roles: ['aicte_admin', 'auditor'], audience: 'AICTE administrators' },
  {
    path: '/blindmatch',
    label: 'Blind Match',
    roles: ['aicte_admin', 'auditor'],
    audience: 'AICTE administrators',
  },
  { path: '/student', label: 'Student', roles: ['student'], audience: 'students' },
  { path: '/verifier', label: 'Verifier', roles: ['verifier', 'aicte_admin'], audience: 'verifiers' },
]

export const ROLE_HOME: Record<Role, string> = {
  institution_admin: '/institution',
  institution_operator: '/institution',
  aicte_admin: '/aicte',
  auditor: '/aicte',
  student: '/student',
  verifier: '/verifier',
}

/** The guarded route a pathname falls under, or undefined for unknown paths (e.g. 404). */
export function routeFor(pathname: string): RouteAccess | undefined {
  if (pathname === '/' || pathname === '') return ROUTES[0]
  return ROUTES.find(
    (route) => route.path !== '/' && (pathname === route.path || pathname.startsWith(`${route.path}/`)),
  )
}

export function canAccess(role: Role, pathname: string): boolean {
  const route = routeFor(pathname)
  return route === undefined || route.roles.includes(role)
}

/** Where to go after switching to ``role``: stay when allowed, else the role's home route. */
export function routeAfterRoleChange(role: Role, pathname: string): string {
  return canAccess(role, pathname) ? pathname : ROLE_HOME[role]
}
