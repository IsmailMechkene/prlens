import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { ApiError, api, hasSeenIntro, isLoginRedirectPending, markIntroSeen } from '../../lib/api'
import { useAsync } from '../../lib/useAsync'
import { AsyncBoundary } from '../ui/AsyncBoundary'
import { LoadingTransition } from '../ui/LoadingTransition'

/**
 * Route guard for the authenticated app shell.
 *
 * Probes GET /api/user. The API client owns the response to a 401 — it drops the
 * dead token and hands the browser to the backend's OAuth entrypoint (see
 * startLogin), which is also what happens when a token expires mid-session on any
 * other call. All this guard does is decide what to paint in the meantime: nothing
 * while that full-page navigation is in flight, and the boundary's error state if
 * the redirect was suppressed (mock mode, or a login that already failed once —
 * without which a backend that keeps rejecting tokens would bounce the browser
 * between the dashboard and GitHub forever).
 *
 * On the first authenticated render after a login it also plays the boot
 * transition over the shell. The shell renders underneath it the whole time, so
 * the pages behind it are fetching their own data while it runs and the fade-out
 * uncovers a dashboard rather than a second round of spinners.
 */
export function RequireAuth() {
  const user = useAsync(() => api.getUser(), [])
  const [intro, setIntro] = useState(() => !hasSeenIntro())

  const unauthenticated = user.error instanceof ApiError && user.error.status === 401

  if (unauthenticated && isLoginRedirectPending()) return null

  return (
    <AsyncBoundary state={user} minHeight={320}>
      {() => (
        <>
          <Outlet />
          {intro && (
            <LoadingTransition
              onComplete={() => {
                markIntroSeen()
                setIntro(false)
              }}
            />
          )}
        </>
      )}
    </AsyncBoundary>
  )
}
