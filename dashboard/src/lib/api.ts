/**
 * Typed PRLens API client.
 *
 * Set `VITE_API_BASE_URL` (e.g. "https://api.example.com" or "/api") to point
 * the dashboard at your backend. When it is unset the client serves the local
 * fixtures in mockData.ts so the UI is fully usable during development.
 *
 * Every method maps 1:1 to an endpoint documented in BACKEND_CONTRACT.md.
 */

import {
  mockDashboardStats,
  mockRepos,
  mockReviews,
  mockUser,
} from './mockData'
import type { DashboardStats, Repo, RepoDetail, RepoSettings, Review, User } from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const USE_MOCKS = BASE_URL === ''

/** Simulate network latency so loading states are exercised in mock mode. */
function mock<T>(value: T): Promise<T> {
  return new Promise((resolve) =>
    setTimeout(() => resolve(structuredClone(value)), 250),
  )
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
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
    visibility: r.visibility,
    updated: r.updated,
    connected: r.connected,
    active: r.active,
  }
}

export const api = {
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

  enableRepo(name: string): Promise<Repo> {
    if (USE_MOCKS) {
      const repo = mockRepos.find((r) => r.name === name)
      if (repo) {
        repo.connected = true
        repo.active = true
      }
      return mock(repo ? stripDetail(repo) : { name, visibility: 'Private', updated: 'just now', connected: true, active: true })
    }
    return request<Repo>(`/repos/${encodeURIComponent(name)}/enable`, { method: 'POST' })
  },
}
