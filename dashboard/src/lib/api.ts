/**
 * Typed PRLens API client.
 *
 * Set `VITE_API_BASE_URL` to the backend's *origin* (e.g. "http://localhost:8000").
 * REST calls are served under `/api` on that origin and the OAuth entrypoint under
 * `/auth`, so both are derived from the one variable. When it is unset the client
 * serves the local fixtures in mockData.ts so the UI is fully usable offline.
 *
 * Every method maps 1:1 to an endpoint documented in BACKEND_CONTRACT.md.
 */

import {
  mockDashboardStats,
  mockRepos,
  mockReviews,
  mockUser,
} from './mockData'
import type {
  DashboardStats,
  DisconnectResult,
  GitHubRepo,
  Repo,
  RepoDetail,
  RepoSettings,
  Review,
  User,
  Visibility,
} from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
export const USE_MOCKS = BASE_URL === ''

const API_ROOT = `${BASE_URL}/api`

/** Where to send the browser to start the GitHub OAuth dance. */
export const githubLoginUrl = `${BASE_URL}/auth/github`

/**
 * Auth is a bearer JWT kept in localStorage, not a session cookie — the backend
 * and dashboard live on different domains, so cookies can't be shared. The OAuth
 * callback redirects to `/dashboard?token=…`; `captureAuthToken` persists that
 * token and every request() below sends it as `Authorization: Bearer …`.
 */
const TOKEN_KEY = 'prlens_token'
/** Marks that an OAuth redirect has already been tried since the last good call. */
const LOGIN_TRIED_KEY = 'prlens_login_tried'

/**
 * Web Storage is not always reachable: reading `window.localStorage` throws a
 * SecurityError when the browser blocks storage (some private-browsing modes,
 * third-party-cookie-blocked iframes), and `setItem` can throw a quota error even
 * when reading works. Every access goes through this wrapper, which keeps an
 * in-memory copy so a storage failure costs the user persistence across reloads
 * rather than white-screening the app on boot.
 */
class SafeStore {
  private memory = new Map<string, string>()
  private backing: Storage | null

  constructor(open: () => Storage) {
    try {
      this.backing = open()
    } catch {
      this.backing = null
    }
  }

  getItem(key: string): string | null {
    try {
      return this.backing?.getItem(key) ?? this.memory.get(key) ?? null
    } catch {
      return this.memory.get(key) ?? null
    }
  }

  setItem(key: string, value: string): void {
    this.memory.set(key, value)
    try {
      this.backing?.setItem(key, value)
    } catch {
      /* keep the in-memory copy */
    }
  }

  removeItem(key: string): void {
    this.memory.delete(key)
    try {
      this.backing?.removeItem(key)
    } catch {
      /* already gone as far as this tab is concerned */
    }
  }
}

const tokenStore = new SafeStore(() => window.localStorage)
const loginStore = new SafeStore(() => window.sessionStorage)

export function getToken(): string | null {
  return tokenStore.getItem(TOKEN_KEY)
}

/** Clear the stored token; the next guarded route will bounce to OAuth. */
export function logout(): void {
  tokenStore.removeItem(TOKEN_KEY)
}

/** True once startLogin() has begun a full-page navigation to GitHub. */
let loginRedirectPending = false

export function isLoginRedirectPending(): boolean {
  return loginRedirectPending
}

/**
 * Hand the browser to the backend's OAuth entrypoint to mint a fresh token.
 *
 * At most one attempt is made per failing session: if the token we come back with
 * is rejected too, redirecting again would spin the browser between the dashboard
 * and GitHub forever. The flag is cleared by the first successful API call, so a
 * later expiry re-authenticates normally.
 *
 * Returns whether a redirect was actually started.
 */
export function startLogin(): boolean {
  if (USE_MOCKS) return false // no backend to log in to
  if (loginRedirectPending) return false
  if (loginStore.getItem(LOGIN_TRIED_KEY)) return false

  loginStore.setItem(LOGIN_TRIED_KEY, '1')
  loginRedirectPending = true
  window.location.href = githubLoginUrl
  return true
}

/**
 * On post-OAuth load the token arrives as a `?token=` query param. Persist it and
 * strip it from the URL so it isn't left in history or shared in links. Must run
 * before React renders (see main.tsx) so the auth guard's first request carries it.
 */
export function captureAuthToken(): void {
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  if (!token) return

  tokenStore.setItem(TOKEN_KEY, token)
  params.delete('token')
  const query = params.toString()
  const url = window.location.pathname + (query ? `?${query}` : '') + window.location.hash
  window.history.replaceState(null, '', url)
}

/** Simulate network latency so loading states are exercised in mock mode. */
function mock<T>(value: T): Promise<T> {
  return new Promise((resolve) =>
    setTimeout(() => resolve(structuredClone(value)), 250),
  )
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const res = await fetch(`${API_ROOT}${path}`, {
    // `init` is spread first: spreading it last would let a caller-supplied
    // `headers` replace the merged object below, dropping the bearer token.
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  })

  // Any endpoint can answer 401 — not just the one the auth guard probes on mount
  // — once a 30-day token expires or the account behind it is gone. Drop the dead
  // token and re-authenticate, instead of leaving the user on a page that can only
  // say "couldn't load data" until they clear storage by hand.
  if (res.status === 401) {
    logout()
    startLogin()
    throw new ApiError(401, `${init?.method ?? 'GET'} ${path} → 401`)
  }

  if (!res.ok) {
    throw new ApiError(res.status, `${init?.method ?? 'GET'} ${path} → ${res.status}`)
  }

  // The token works, so a future 401 is a fresh expiry and may redirect again.
  loginStore.removeItem(LOGIN_TRIED_KEY)

  return (await res.json()) as T
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function stripDetail(r: RepoDetail): Repo {
  return {
    name: r.name,
    owner: r.owner,
    visibility: r.visibility,
    updated: r.updated,
    connected: r.connected,
    active: r.active,
  }
}

function toGitHubRepo(r: RepoDetail): GitHubRepo {
  return {
    name: r.name,
    owner: r.owner,
    visibility: r.visibility,
    updated: r.updated,
    connected: r.connected,
  }
}

export interface HealthCheck {
  ok: boolean
  latencyMs: number
}

export const api = {
  /**
   * Pings the backend's root health endpoint (`GET /`, outside `/api`).
   * Resolves with `ok: false` instead of rejecting so callers can render
   * an outage state without try/catch.
   */
  async getHealth(): Promise<HealthCheck> {
    if (USE_MOCKS) return mock({ ok: true, latencyMs: 42 })
    const started = performance.now()
    try {
      const res = await fetch(`${BASE_URL}/`, { signal: AbortSignal.timeout(8000) })
      return { ok: res.ok, latencyMs: Math.round(performance.now() - started) }
    } catch {
      return { ok: false, latencyMs: Math.round(performance.now() - started) }
    }
  },

  getUser(): Promise<User> {
    if (USE_MOCKS) return mock(mockUser)
    return request<User>('/user')
  },

  getDashboardStats(): Promise<DashboardStats> {
    if (USE_MOCKS) return mock(mockDashboardStats)
    return request<DashboardStats>('/stats')
  },

  getReviews(limit = 10): Promise<Review[]> {
    if (USE_MOCKS) return mock(mockReviews.slice(0, limit))
    return request<Review[]>(`/reviews?limit=${limit}`)
  },

  getRepos(): Promise<Repo[]> {
    if (USE_MOCKS) return mock(mockRepos.map(stripDetail))
    return request<Repo[]>('/repos')
  },

  /**
   * Every repo the signed-in user can see on GitHub, each flagged with whether
   * PRLens is already installed. Backed by the user's OAuth token, so it lists
   * repos that have no Installation row yet — unlike getRepos().
   */
  getGitHubRepos(): Promise<GitHubRepo[]> {
    if (USE_MOCKS) return mock(mockRepos.map(toGitHubRepo))
    return request<GitHubRepo[]>('/github/repos')
  },

  getRepo(name: string): Promise<RepoDetail> {
    if (USE_MOCKS) {
      const repo = mockRepos.find((r) => r.name === name)
      if (!repo) return Promise.reject(new ApiError(404, `repo ${name} not found`))
      return mock(repo)
    }
    return request<RepoDetail>(`/repos/${encodeURIComponent(name)}`)
  },

  getRepoReviews(name: string): Promise<Review[]> {
    if (USE_MOCKS) {
      const own = mockReviews.filter((r) => r.repo === name)
      const filler = mockReviews.filter((r) => r.repo !== name)
      // Pad to at least 4 rows like the design does.
      while (own.length < 4 && filler.length) own.push(filler.shift()!)
      return mock(own)
    }
    return request<Review[]>(`/repos/${encodeURIComponent(name)}/reviews`)
  },

  updateRepoSettings(name: string, settings: RepoSettings): Promise<RepoSettings> {
    if (USE_MOCKS) {
      const repo = mockRepos.find((r) => r.name === name)
      if (repo) repo.settings = structuredClone(settings)
      return mock(settings)
    }
    return request<RepoSettings>(`/repos/${encodeURIComponent(name)}/settings`, {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
  },

  setRepoActive(name: string, active: boolean): Promise<{ active: boolean }> {
    if (USE_MOCKS) {
      const repo = mockRepos.find((r) => r.name === name)
      if (repo) repo.active = active
      return mock({ active })
    }
    return request<{ active: boolean }>(`/repos/${encodeURIComponent(name)}/active`, {
      method: 'PUT',
      body: JSON.stringify({ active }),
    })
  },

  enableRepo(name: string, owner: string, visibility: Visibility): Promise<Repo> {
    if (USE_MOCKS) {
      const repo = mockRepos.find((r) => r.name === name)
      if (repo) {
        repo.connected = true
        repo.active = true
      }
      return mock(repo ? stripDetail(repo) : { name, owner, visibility, updated: 'just now', connected: true, active: true })
    }
    return request<Repo>(`/repos/${encodeURIComponent(name)}/enable`, {
      method: 'POST',
      body: JSON.stringify({ owner, visibility }),
    })
  },

  /**
   * Remove PRLens from a repo entirely: its installation, settings and review
   * history, plus the repo's attachment to the PRLens GitHub App. Destructive and
   * not undoable — see `githubRemoved` on the result for the GitHub half, which is
   * best-effort.
   */
  disconnectRepo(name: string): Promise<DisconnectResult> {
    if (USE_MOCKS) {
      const repo = mockRepos.find((r) => r.name === name)
      if (repo) {
        repo.connected = false
        repo.active = false
      }
      return mock({ name, githubRemoved: true })
    }
    return request<DisconnectResult>(`/repos/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    })
  },
}
