// Owner: Dev D
import { NavLink, Outlet } from 'react-router-dom'
import { useMockMode } from '../lib/api'
import { ROLES, setIdentity, useIdentity, type Role } from '../lib/roles'

interface NavItem {
  to: string
  label: string
  roles: readonly Role[]
}

const NAV: NavItem[] = [
  { to: '/', label: 'Home', roles: ROLES },
  { to: '/institution', label: 'Institution', roles: ['institution_admin', 'institution_operator'] },
  { to: '/aicte', label: 'AICTE', roles: ['aicte_admin', 'auditor'] },
  { to: '/blindmatch', label: 'Blind Match', roles: ['aicte_admin', 'auditor'] },
  { to: '/student', label: 'Student', roles: ['student'] },
  { to: '/verifier', label: 'Verifier', roles: ['verifier', 'aicte_admin'] },
]

export default function Layout() {
  const { role } = useIdentity()
  const mock = useMockMode()

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3">
          <span className="text-lg font-semibold">APAAR Integrity Platform</span>
          {mock && (
            <span
              className="rounded bg-amber-100 px-2 py-0.5 text-xs font-bold tracking-wide text-amber-800"
              title="The API is returning mock fixtures"
            >
              MOCK
            </span>
          )}
          <nav className="flex flex-wrap gap-3 text-sm">
            {NAV.filter((item) => item.roles.includes(role)).map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  isActive ? 'font-semibold text-blue-700' : 'text-slate-600 hover:text-slate-900'
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <label className="ml-auto flex items-center gap-2 text-sm">
            <span className="text-slate-500">Demo role</span>
            <select
              className="rounded border border-slate-300 bg-white px-2 py-1"
              value={role}
              onChange={(event) => setIdentity({ role: event.target.value as Role })}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
