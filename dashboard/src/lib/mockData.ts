/**
 * Development fixtures.
 *
 * Used only when no backend is configured (VITE_API_BASE_URL unset) so the
 * UI is fully viewable before the real API exists. The shapes here are the
 * source of truth for BACKEND_CONTRACT.md — keep them in sync.
 */

import type {
  AdminInstallation,
  AdminReview,
  AdminUser,
  DashboardStats,
  RepoDetail,
  Review,
  User,
} from './types'

export const mockRepos: RepoDetail[] = [
  makeRepo('api-gateway', 'Private', '2h ago', true, true, {
    description:
      "Edge API gateway with routing, rate limiting and JWT auth. PRLens reviews every PR against your team's ruleset.",
    scoreTrend: [72, 70, 74, 73, 76, 71, 75, 78, 74, 77, 79, 76, 80, 78, 82, 79, 83, 81, 80, 84, 82, 85, 83, 86, 84, 87, 85, 88, 86, 84],
    currentScore: 84,
    scoreDelta: 6,
    issues: [
      { category: 'Security', value: 8 },
      { category: 'Quality', value: 15 },
      { category: 'Performance', value: 5 },
      { category: 'Style', value: 12 },
    ],
    settings: {
      minSeverity: 'warning',
      languages: { Python: true, JavaScript: true, TypeScript: true, Java: false },
      approveThreshold: 80,
      changesThreshold: 50,
      excluded: ['*.lock', 'dist/**'],
      reviewerMap: [
        { key: 'security', value: '@acme/appsec' },
        { key: 'performance', value: '@dkessler' },
      ],
    },
  }),
  makeRepo('web-app', 'Private', '5h ago', true, true),
  makeRepo('design-system', 'Public', 'yesterday', true, false),
  makeRepo('billing-service', 'Private', '3d ago', true, true),
  makeRepo('docs', 'Public', '1d ago', false, false),
  makeRepo('infra-terraform', 'Private', '6h ago', false, false),
  makeRepo('mobile-ios', 'Private', '4d ago', false, false),
  makeRepo('analytics-pipeline', 'Private', '2w ago', false, false),
]

export const mockReviews: Review[] = [
  { repo: 'api-gateway', number: 482, title: 'Add JWT auth middleware to gateway', score: 42, status: 'changes_requested', reviewedAt: '2h ago' },
  { repo: 'web-app', number: 1207, title: 'Refactor checkout flow to server actions', score: 88, status: 'approved', reviewedAt: '4h ago' },
  { repo: 'billing-service', number: 96, title: 'Retry logic for Stripe webhooks', score: 74, status: 'changes_requested', reviewedAt: '6h ago' },
  { repo: 'design-system', number: 340, title: 'Tokenize spacing scale', score: 91, status: 'approved', reviewedAt: 'yesterday' },
  { repo: 'api-gateway', number: 479, title: 'Rate limit per API key', score: 83, status: 'approved', reviewedAt: 'yesterday' },
  { repo: 'web-app', number: 1198, title: 'Dark mode persistence bug', score: 38, status: 'incomplete', reviewedAt: '2d ago' },
  { repo: 'billing-service', number: 91, title: 'Migrate invoices table', score: 67, status: 'changes_requested', reviewedAt: '3d ago' },
]

export const mockDashboardStats: DashboardStats = {
  stats: [
    { id: 'prs', label: 'PRs reviewed', value: '1,284', delta: '+42 this wk', trend: 'up', icon: 'git-pull-request', iconColor: 'var(--pa)' },
    { id: 'score', label: 'Average score', value: '81', delta: '+3 pts', trend: 'up', icon: 'gauge', iconColor: 'var(--success)' },
    { id: 'issues', label: 'Issues caught', value: '3,907', delta: '+128', trend: 'neutral', icon: 'shield-alert', iconColor: 'var(--danger)' },
    { id: 'repos', label: 'Repos connected', value: '4', delta: '4 active', trend: 'neutral', icon: 'book-marked', iconColor: 'var(--done)' },
  ],
}

/**
 * The mock user is an admin, so the admin section is reachable in mock mode —
 * otherwise it could only ever be seen against a real backend with a promoted
 * account, which is exactly the kind of page that then rots unnoticed.
 */
export const mockUser: User = {
  name: 'Dana Kessler',
  handle: '@dkessler',
  initials: 'DK',
  role: 'admin',
}

export const mockAdminStats: DashboardStats = {
  stats: [
    { id: 'users', label: 'Users', value: '38', delta: '2 admin', trend: 'neutral', icon: 'users', iconColor: 'var(--pa)' },
    { id: 'repos', label: 'Repos connected', value: '112', delta: '97 active', trend: 'neutral', icon: 'git-branch', iconColor: 'var(--done)' },
    { id: 'reviews', label: 'Reviews run', value: '4,061', delta: '+215 this wk', trend: 'up', icon: 'git-pull-request', iconColor: 'var(--success)' },
    { id: 'failures', label: 'Failed reviews', value: '37', delta: '1% of runs', trend: 'down', icon: 'shield-alert', iconColor: 'var(--danger)' },
  ],
}

export const mockAdminUsers: AdminUser[] = [
  { id: 1, name: 'Dana Kessler', handle: '@dkessler', initials: 'DK', role: 'admin', repos: 4, reviews: 128, lastActive: '2h ago' },
  { id: 2, name: 'Ismail Mechkene', handle: '@imechkene', initials: 'IM', role: 'admin', repos: 6, reviews: 402, lastActive: '40m ago' },
  { id: 3, name: 'Priya Raman', handle: '@praman', initials: 'PR', role: 'user', repos: 3, reviews: 76, lastActive: 'yesterday' },
  { id: 4, name: 'Tom Alvarez', handle: '@talvarez', initials: 'TA', role: 'user', repos: 2, reviews: 19, lastActive: '5d ago' },
  { id: 5, name: 'Wei Chen', handle: '@wchen', initials: 'WC', role: 'user', repos: 1, reviews: 0, lastActive: '—' },
]

export const mockAdminInstallations: AdminInstallation[] = [
  { name: 'api-gateway', owner: 'acme', visibility: 'Private', updated: '2h ago', connected: true, active: true, userId: 1, user: '@dkessler' },
  { name: 'api-gateway', owner: 'acme', visibility: 'Private', updated: '3h ago', connected: true, active: false, userId: 3, user: '@praman' },
  { name: 'web-app', owner: 'acme', visibility: 'Private', updated: '5h ago', connected: true, active: true, userId: 1, user: '@dkessler' },
  { name: 'billing-service', owner: 'acme', visibility: 'Private', updated: '3d ago', connected: true, active: true, userId: 2, user: '@imechkene' },
  { name: 'design-system', owner: 'acme', visibility: 'Public', updated: 'yesterday', connected: true, active: false, userId: 4, user: '@talvarez' },
]

export const mockAdminReviews: AdminReview[] = [
  { repo: 'api-gateway', number: 482, title: 'Add JWT auth middleware to gateway', score: 42, status: 'changes_requested', reviewedAt: '2h ago', user: '@dkessler' },
  { repo: 'billing-service', number: 96, title: 'Retry logic for Stripe webhooks', score: 0, status: 'total_failure', reviewedAt: '3h ago', user: '@imechkene' },
  { repo: 'web-app', number: 1207, title: 'Refactor checkout flow to server actions', score: 88, status: 'approved', reviewedAt: '4h ago', user: '@dkessler' },
  { repo: 'web-app', number: 1198, title: 'Dark mode persistence bug', score: 38, status: 'incomplete', reviewedAt: '2d ago', user: '@praman' },
  { repo: 'design-system', number: 340, title: 'Tokenize spacing scale', score: 91, status: 'approved', reviewedAt: 'yesterday', user: '@talvarez' },
]

/** Default settings applied to repos without a stored config. */
function defaultDetailExtras(): Omit<RepoDetail, keyof import('./types').Repo | 'owner'> {
  return {
    description: 'PRLens reviews every pull request against your team ruleset.',
    scoreTrend: [70, 72, 71, 74, 73, 76, 78, 75, 79, 81, 80, 82, 84, 83, 85],
    currentScore: 82,
    scoreDelta: 4,
    issues: [
      { category: 'Security', value: 4 },
      { category: 'Quality', value: 11 },
      { category: 'Performance', value: 3 },
      { category: 'Style', value: 7 },
    ],
    settings: {
      minSeverity: 'warning',
      languages: { Python: true, JavaScript: true, TypeScript: true, Java: false },
      approveThreshold: 80,
      changesThreshold: 50,
      excluded: ['*.lock', 'dist/**'],
      reviewerMap: [{ key: 'security', value: '@acme/appsec' }],
    },
  }
}

function makeRepo(
  name: string,
  visibility: RepoDetail['visibility'],
  updated: string,
  connected: boolean,
  active: boolean,
  overrides: Partial<RepoDetail> = {},
): RepoDetail {
  return {
    name,
    owner: 'acme',
    visibility,
    updated,
    connected,
    active,
    ...defaultDetailExtras(),
    ...overrides,
  }
}
