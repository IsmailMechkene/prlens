import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { ApiError, api, githubLoginUrl, USE_MOCKS } from '../../lib/api'
import { useAsync } from '../../lib/useAsync'
import { AsyncBoundary } from '../ui/AsyncBoundary'

/**
 * Route guard for the authenticated app shell.
 *
 * Probes GET /api/user; a 401 means there is no valid bearer token (missing or
 * expired), so the browser is handed to the backend's OAuth entrypoint, which
 * mints a fresh token. In mock mode there is no backend to log in to, so the
 * guard is inert.
 */
export function RequireAuth() {
  const user = useAsync(() => api.getUser(), [])

  const unauthenticated = user.error instanceof ApiError && user.error.status === 401

  useEffect(() => {
    if (unauthenticated && !USE_MOCKS) {
      // Full page navigation, not a router push: the OAuth flow leaves the SPA.
      window.location.href = githubLoginUrl
    }
  }, [unauthenticated])

  // Render nothing while the redirect above is in flight, rather than flashing
  // the AsyncBoundary's "Couldn't load data" error state.
  if (unauthenticated) return null

  return (
    <AsyncBoundary state={user} minHeight={320}>
      {() => <Outlet />}
    </AsyncBoundary>
  )
}
