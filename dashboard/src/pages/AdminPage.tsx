import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync } from '../lib/useAsync'
import type { AdminReview, AdminUser } from '../lib/types'
import { Card } from '../components/ui/Card'
import { Icon } from '../components/ui/Icon'
import { ScoreBadge } from '../components/ui/ScoreBadge'
import { StatusBadge } from '../components/ui/StatusBadge'
import { AsyncBoundary } from '../components/ui/AsyncBoundary'
import { Skeleton } from '../components/ui/Skeleton'
import { PageHeader } from '../components/layout/PageHeader'
import { StatCard } from '../components/dashboard/StatCard'
import styles from './AdminPage.module.css'

const statsSkeleton = (
  <>
    {[0, 1, 2, 3].map((i) => (
      <Card key={i} className={styles.statSkeleton}>
        <div className={styles.statSkeletonLabel}>
          <Skeleton width={15} height={15} radius="50%" />
          <Skeleton width={96} height={12} />
        </div>
        <Skeleton width={54} height={26} />
      </Card>
    ))}
  </>
)

function rowsSkeleton(widths: string[]) {
  return (
    <div>
      {[0, 1, 2, 3, 4].map((i) => (
        <div key={i} className={styles.rowSkeleton}>
          {widths.map((w, j) => (
            <Skeleton key={j} width={w} />
          ))}
        </div>
      ))}
    </div>
  )
}

function UsersTable({ users }: { users: AdminUser[] }) {
  const navigate = useNavigate()

  if (users.length === 0) {
    return <div className={styles.empty}>No accounts yet.</div>
  }

  return (
    <div className={styles.scroll}>
      <table className={styles.table}>
        <thead>
          <tr className={styles.headRow}>
            <th className={styles.th}>User</th>
            <th className={styles.th}>Role</th>
            <th className={styles.th}>Repos</th>
            <th className={styles.th}>Reviews</th>
            <th className={`${styles.th} ${styles.right}`}>Last review</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className={styles.row} onClick={() => navigate(`/admin/users/${u.id}`)}>
              <td className={styles.td}>
                <span className={styles.user}>
                  <span className={styles.avatar}>{u.initials}</span>
                  <span>
                    <span className={styles.userName}>{u.name}</span>
                    <span className={styles.userHandle}>{u.handle}</span>
                  </span>
                </span>
              </td>
              <td className={styles.td}>
                {u.role === 'admin' ? (
                  <span className={styles.adminTag}>Admin</span>
                ) : (
                  <span className={styles.muted}>User</span>
                )}
              </td>
              <td className={styles.td}>{u.repos}</td>
              <td className={styles.td}>{u.reviews}</td>
              <td className={`${styles.td} ${styles.right} ${styles.date}`}>{u.lastActive}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * The global review feed. Deliberately not the dashboard's ReviewsTable: its rows
 * link to /repos/{name}, which is scoped to the signed-in user's own installations
 * — following one of those for somebody else's repo would only ever 404.
 */
function FeedTable({ reviews }: { reviews: AdminReview[] }) {
  if (reviews.length === 0) {
    return <div className={styles.empty}>Nothing to show.</div>
  }

  return (
    <div className={styles.scroll}>
      <table className={styles.table}>
        <thead>
          <tr className={styles.headRow}>
            <th className={styles.th}>User</th>
            <th className={styles.th}>Repository</th>
            <th className={styles.th}>Pull request</th>
            <th className={styles.th}>Score</th>
            <th className={styles.th}>Status</th>
            <th className={`${styles.th} ${styles.right}`}>Reviewed</th>
          </tr>
        </thead>
        <tbody>
          {reviews.map((rv) => (
            <tr key={`${rv.user}-${rv.repo}-${rv.number}`} className={styles.staticRow}>
              <td className={`${styles.td} ${styles.muted}`}>{rv.user}</td>
              <td className={styles.td}>
                <span className={styles.repo}>
                  <Icon name="book-marked" size={14} className={styles.repoIcon} />
                  {rv.repo}
                </span>
              </td>
              <td className={`${styles.td} ${styles.prCell}`}>
                <span className={styles.prNum}>#{rv.number}</span>
                {rv.title}
              </td>
              <td className={styles.td}>
                <ScoreBadge score={rv.score} />
              </td>
              <td className={styles.td}>
                <StatusBadge status={rv.status} />
              </td>
              <td className={`${styles.td} ${styles.right} ${styles.date}`}>{rv.reviewedAt}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Deployment-wide view: every account, every connected repo, every review PRLens
 * has run — as opposed to /dashboard, which only ever shows the signed-in user's
 * own. Both are ordinary routes and an admin moves between them freely; this is a
 * second view, not a mode the account is switched into.
 *
 * Read-only throughout. Nothing here edits another user's repos or settings, and
 * the admin role itself is granted out of band (scripts/set_admin.py) rather than
 * from a button, so a compromised admin session cannot mint more admins.
 */
export function AdminPage() {
  const [failedOnly, setFailedOnly] = useState(false)

  const stats = useAsync(() => api.getAdminStats(), [])
  const users = useAsync(() => api.getAdminUsers(), [])
  const reviews = useAsync(() => api.getAdminReviews(failedOnly ? 'failed' : undefined), [failedOnly])

  return (
    <div className={styles.container}>
      <PageHeader
        title="Admin"
        subtitle="Every account, repository and review across this PRLens deployment."
      />

      <div className={styles.stats}>
        <AsyncBoundary state={stats} minHeight={92} skeleton={statsSkeleton}>
          {(data) => data.stats.map((s) => <StatCard key={s.id} stat={s} />)}
        </AsyncBoundary>
      </div>

      <Card flush className={styles.panel}>
        <div className={styles.tableHead}>
          <h2 className={styles.tableTitle}>Users</h2>
        </div>
        <AsyncBoundary
          state={users}
          minHeight={160}
          skeleton={rowsSkeleton(['26%', '10%', '8%', '8%', '14%'])}
        >
          {(data) => <UsersTable users={data} />}
        </AsyncBoundary>
      </Card>

      <Card flush>
        <div className={styles.tableHead}>
          <h2 className={styles.tableTitle}>Recent reviews</h2>
          {/* A run of failures across unrelated repos and users is what an outage of
              the LLM backend looks like from here — worth one click to isolate. */}
          <button
            type="button"
            className={`${styles.filter} ${failedOnly ? styles.filterOn : ''}`}
            aria-pressed={failedOnly}
            onClick={() => setFailedOnly((v) => !v)}
          >
            <Icon name="shield-alert" size={14} /> Failures only
          </button>
        </div>
        <AsyncBoundary
          state={reviews}
          minHeight={160}
          skeleton={rowsSkeleton(['12%', '16%', '30%', '8%', '12%', '10%'])}
        >
          {(data) => <FeedTable reviews={data} />}
        </AsyncBoundary>
      </Card>
    </div>
  )
}
