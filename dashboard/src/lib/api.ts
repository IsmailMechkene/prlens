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

/** Simulate network latency so loading states are exercised in mock mode. */
function mock<T>(value: T): Promise<T> {
  return new Promise((resolve) =>
    setTimeout(() => resolve(structuredClone(value)), 250),
  )
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_ROOT}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    credentials: 'include',
    ...init,
  })
  if (!res.ok) {
    throw new ApiError(res.status, `${init?.method ?? 'GET'} ${path} → ${res.status}`)
  }
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
}
