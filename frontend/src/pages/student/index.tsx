// Owner: Dev E
import { useQuery } from '@tanstack/react-query'
import QueryView from '../../components/QueryView'
import { api } from '../../lib/api'
import { useIdentity } from '../../lib/roles'

// TODO: switch to components['schemas']['StudentRecords'] from ../../lib/api-types once gen:api runs.
interface StudentRecords {
  student: { id: string; full_name: string }
  admissions: unknown[]
}

export default function StudentPage() {
  const { role } = useIdentity()
  const query = useQuery({
    queryKey: ['my-records', role],
    queryFn: () => api<StudentRecords>('/students/me/records'),
  })
  return <QueryView title="My records" endpoint="/students/me/records" query={query} />
}
