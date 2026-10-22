// Owner: Dev D
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import QueryView from '../../components/QueryView'
import { API_URL, api } from '../../lib/api'

interface Health {
  status: string
  mock_mode: boolean
  engine_import_ok: boolean
  version: string
}

const LINKS = [
  { to: '/institution', label: 'Institution: seat ledger and uploads' },
  { to: '/aicte', label: 'AICTE: review cases and monitoring' },
  { to: '/blindmatch', label: 'Blind Match: privacy-preserving duplicates' },
  { to: '/student', label: 'Student: records, consents, credentials' },
  { to: '/verifier', label: 'Verifier: check a credential QR' },
]

export default function HomePage() {
  const health = useQuery({ queryKey: ['health'], queryFn: () => api<Health>('/health') })

  return (
    <div className="space-y-6">
      <p className="text-slate-600">
        Verifiable, consent-first student records for AICTE-approved institutions.
      </p>
      <ul className="list-disc space-y-1 pl-6">
        {LINKS.map((link) => (
          <li key={link.to}>
            <Link className="text-blue-700 hover:underline" to={link.to}>
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
      <QueryView title="API health" endpoint={`${API_URL}/health`} query={health} />
    </div>
  )
}
