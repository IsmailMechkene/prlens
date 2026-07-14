import { Navigate, Outlet } from 'react-router-dom'
import { api } from '../../lib/api'
import { useAsync } from '../../lib/useAsync'
import { AsyncBoundary } from '../ui/AsyncBoundary'

/**
 * Route guard for the admin section. Nests *inside* RequireAuth, which has already
 * established that there is a session — all this adds is the role check.
 *
 * This is a UX guard, not the access control: it keeps a non-admin who types /admin
 * from landing on a page of failed requests. The real check is server-side, where
 * every /api/admin route re-reads the role from the user's database row, so hiding
 * the link or bouncing the route is never the only thing standing between a normal
 * user and another user's data.
 *
 * A non-admin is sent to their own dashboard rather than shown an error — from
 * their side the admin section does not exist.
 */
export function RequireAdmin() {
  const user = useAsync(() => api.getUser(), [])

  return (
    <AsyncBoundary state={user} minHeight={320}>
      {(data) => (data.role === 'admin' ? <Outlet /> : <Navigate to="/dashboard" replace />)}
    </AsyncBoundary>
  )
}
