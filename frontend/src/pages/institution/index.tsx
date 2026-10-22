// Owner: Dev D
import { useQuery } from '@tanstack/react-query'
import QueryView from '../../components/QueryView'
import { api } from '../../lib/api'
import { useIdentity } from '../../lib/roles'

// TODO: switch to components['schemas']['SeatLedger'] from ../../lib/api-types once gen:api runs.
interface SeatLedger {
  institution_id: string
  academic_year: string
  programmes: unknown[]
}

export default function InstitutionPage() {
  const { role, institutionId } = useIdentity()
  const path = `/institutions/${institutionId}/seat-ledger?academic_year=2026-27`
  const query = useQuery({
    queryKey: ['seat-ledger', institutionId, role],
    queryFn: () => api<SeatLedger>(path),
  })
  return <QueryView title="Seat Ledger 2026-27" endpoint={path} query={query} />
}
