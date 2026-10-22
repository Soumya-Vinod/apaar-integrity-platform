// Owner: Dev D
import { useQuery } from '@tanstack/react-query'
import QueryView from '../../components/QueryView'
import { api } from '../../lib/api'
import { useIdentity } from '../../lib/roles'

// TODO: switch to components['schemas']['BlindMatchCase'] from ../../lib/api-types once gen:api runs.
interface BlindMatchCase {
  id: string
  dice: number
  status: string
}

export default function BlindMatchPage() {
  const { role } = useIdentity()
  const query = useQuery({
    queryKey: ['blind-match-cases', role],
    queryFn: () => api<BlindMatchCase[]>('/blind-match/cases'),
  })
  return <QueryView title="Blind Match cases" endpoint="/blind-match/cases" query={query} />
}
