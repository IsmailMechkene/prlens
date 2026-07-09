/**
 * Domain models for PRLens.
 *
 * These are the shapes the frontend expects from the backend API.
 * The backend contract (endpoints + JSON shapes) is documented in
 * BACKEND_CONTRACT.md at the project root.
 */

/** The signed-in user. */
export interface User {
  name: string
  handle: string
  /** Two-letter avatar fallback. */
  initials: string
  /** Optional avatar image URL. */
  avatarUrl?: string
}

export type Visibility = 'Public' | 'Private'

/**
 * The verdict PRLens submitted on the pull request. These are the values of the
 * agent's `ReviewOutcome` enum (prlens/github/pr_publisher.py), persisted
 * verbatim on `Review.status`.
 */
export type ReviewStatus =
  | 'approved'
  | 'changes_requested'
  | 'comment'
  | 'incomplete'
  | 'total_failure'

export type Severity = 'info' | 'warning' | 'error' | 'critical'

export type IssueCategory = 'Security' | 'Quality' | 'Performance' | 'Style'

/** A repository connected to (or connectable by) PRLens. */
export interface Repo {
  /** Short name without owner, e.g. "api-gateway". */
  name: string
  /** Owning user or org, e.g. "acme". */
  owner: string
  visibility: Visibility
  /** Human-readable "last updated", e.g. "2h ago". */
  updated: string
  /** Whether PRLens is installed on this repo. */
  connected: boolean
  /** Whether reviewing is currently enabled. */
  active: boolean
}

/**
 * A repository as GitHub reports it, before PRLens is installed on it.
 * `active` only exists once there is an Installation row, so it is absent here.
 */
export type GitHubRepo = Omit<Repo, 'active'>

/** A single PR review result. */
export interface Review {
  /** Repo short name this review belongs to. */
  repo: string
  /** Pull request number. */
  number: number
  title: string
  /** Quality score 0–100. */
  score: number
  status: ReviewStatus
  /** Human-readable relative time, e.g. "2h ago". */
  reviewedAt: string
}

/** A single metric tile on the dashboard. */
export interface Stat {
  id: string
  label: string
  value: string
  delta: string
  /** 'up' | 'down' | 'neutral' — drives the delta colour. */
  trend: 'up' | 'down' | 'neutral'
  /** lucide icon name. */
  icon: string
  /** Icon accent colour (CSS colour or var). */
  iconColor: string
}

/** Aggregate dashboard metrics. */
export interface DashboardStats {
  stats: Stat[]
}

/** One slice of the issues-breakdown donut. */
export interface IssueBreakdown {
  category: IssueCategory
  value: number
}

/** Per-repo review configuration. */
export interface RepoSettings {
  minSeverity: Severity
  languages: Record<string, boolean>
  approveThreshold: number
  changesThreshold: number
  excluded: string[]
  reviewerMap: { key: string; value: string }[]
}

/** Full repo detail payload for the repo page. */
export interface RepoDetail extends Repo {
  description: string
  /** Daily quality scores, oldest → newest (for the trend chart). */
  scoreTrend: number[]
  currentScore: number
  /** Change vs. start of window, e.g. +6. */
  scoreDelta: number
  issues: IssueBreakdown[]
  settings: RepoSettings
}
