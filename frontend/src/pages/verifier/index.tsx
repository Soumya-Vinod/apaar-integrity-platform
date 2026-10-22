// Owner: Dev E
import { useQuery } from '@tanstack/react-query'
import QueryView from '../../components/QueryView'
import { api } from '../../lib/api'

// TODO: switch to components['schemas']['PublicKey'] from ../../lib/api-types once gen:api runs.
interface PublicKey {
  algorithm: 'Ed25519'
  key_id: string
  public_key_b64: string
}

export default function VerifierPage() {
  const query = useQuery({
    queryKey: ['credentials-public-key'],
    queryFn: () => api<PublicKey>('/credentials/public-key'),
  })
  return <QueryView title="Credential public key" endpoint="/credentials/public-key" query={query} />
}
