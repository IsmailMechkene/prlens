/**
 * Domain models for PRLens.
 *
 * These are the shapes the frontend expects from the backend API.
 * The backend contract (endpoints + JSON shapes) is documented in
 * BACKEND_CONTRACT.md at the project root.
 */

/**
 * A user's privilege level. `admin` unlocks the deployment-wide admin section on
 * top of the ordinary dashboard — it does not replace it. Granted only out of band
 * (scripts/set_admin.py); there is no way to change it from the UI.
 */
export type Role = 'user' | 'admin'

/** The signed-in user. */
export interface User {
  name: string
  handle: string
  /** Two-letter avatar fallback. */
  initials: string
  /** Optional avatar image URL. */
  avatarUrl?: string
  /**
   * Drives whether the admin section is offered. A hint for the UI only: hiding
   * the link is not the access control — every /api/admin route re-checks the role
   * server-side, so a hand-typed /admin URL still gets a 403.
   */
  role: Role
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

/**
 * The result of enabling a repo. Enabling records the repo in PRLens, but GitHub
 * only delivers pull requests once the PRLens App is installed on the account that
 * owns it — which the owner has to do on GitHub. `appInstalled: false` means it has
 * not been, and no review will ever arrive until the user visits `installUrl`.
 * `null` means the check itself failed, and nothing should be claimed either way.
 */
export interface EnableResult extends Repo {
  appInstalled: boolean | null
  installUrl: string | null
}

/**
 * Outcome of removing PRLens from a repo. `githubRemoved` is whether the repo was
 * also detached from the PRLens GitHub App — if it is false the dashboard rows are
 * gone but GitHub may still deliver pull requests for review.
 */
export interface DisconnectResult {
  name: string
  githubRemoved: boolean
}

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

/* ---------------------------------------------------------------------------
 * Admin
 *
 * These shapes come from /api/admin/*, which is scoped to the whole deployment
 * rather than to the signed-in user, and is read-only: the admin section reports,
 * it does not administer other people's repos.
 * ------------------------------------------------------------------------- */

/** One account, as the admin users list sees it. */
export interface AdminUser {
  id: number
  name: string
  handle: string
  initials: string
  avatarUrl?: string
  role: Role
  /** Number of repos this user has connected. */
  repos: number
  /** Number of reviews recorded across them. */
  reviews: number
  /** Relative time of their most recent review, or "—" if they have none. */
  lastActive: string
}

/** One account in full: the counts above, plus the rows behind them. */
export interface AdminUserDetail extends AdminUser {
  installations: Repo[]
  recentReviews: Review[]
}

/** An installation as the admin sees it — with the user it belongs to. */
export interface AdminInstallation extends Repo {
  userId: number
  /** Handle of the user who connected it. */
  user: string
}

/** A review in the global feed, tagged with whose installation recorded it. */
export interface AdminReview extends Review {
  user: string
}
