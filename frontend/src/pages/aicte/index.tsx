// Owner: Dev D
import { useQuery } from '@tanstack/react-query'
import QueryView from '../../components/QueryView'
import { api } from '../../lib/api'
import { useIdentity } from '../../lib/roles'

// TODO: switch to components['schemas']['ReviewCase'] from ../../lib/api-types once gen:api runs.
interface ReviewCase {
  id: string
  kind: string
  title: string
  status: string
}

export default function AictePage() {
  const { role } = useIdentity()
  const query = useQuery({
    queryKey: ['review-cases', role],
    queryFn: () => api<ReviewCase[]>('/review-cases'),
  })
  return <QueryView title="Review cases" endpoint="/review-cases" query={query} />
}
