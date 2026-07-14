import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync } from '../lib/useAsync'
import type { AdminUserDetail } from '../lib/types'
import { Card } from '../components/ui/Card'
import { Icon } from '../components/ui/Icon'
import { ScoreBadge } from '../components/ui/ScoreBadge'
import { StatusBadge } from '../components/ui/StatusBadge'
import { AsyncBoundary } from '../components/ui/AsyncBoundary'
import { PageHeader } from '../components/layout/PageHeader'
import styles from './AdminUserPage.module.css'

function Detail({ user }: { user: AdminUserDetail }) {
  return (
    <>
      <PageHeader
        title={user.name}
        subtitle={
          <>
            {user.handle} · {user.repos} {user.repos === 1 ? 'repo' : 'repos'} ·{' '}
            {user.reviews} {user.reviews === 1 ? 'review' : 'reviews'} · last review{' '}
            {user.lastActive}
          </>
        }
      />

      <Card flush className={styles.panel}>
        <div className={styles.tableHead}>
          <h2 className={styles.tableTitle}>Repositories</h2>
        </div>
        {user.installations.length === 0 ? (
          // The first thing to check when somebody reports "PRLens isn't reviewing
          // my repo": whether it was ever connected at all.
          <div className={styles.empty}>This user has not connected any repository.</div>
        ) : (
          <div className={styles.scroll}>
            <table className={styles.table}>
              <thead>
                <tr className={styles.headRow}>
                  <th className={styles.th}>Repository</th>
                  <th className={styles.th}>Visibility</th>
                  <th className={styles.th}>Reviewing</th>
                  <th className={`${styles.th} ${styles.right}`}>Connected</th>
                </tr>
              </thead>
              <tbody>
                {user.installations.map((repo) => (
                  <tr key={repo.name} className={styles.staticRow}>
                    <td className={styles.td}>
                      <span className={styles.repo}>
                        <Icon
                          name={repo.visibility === 'Public' ? 'book' : 'lock'}
                          size={14}
                          className={styles.repoIcon}
                        />
                        {repo.name}
                      </span>
                    </td>
                    <td className={`${styles.td} ${styles.muted}`}>{repo.visibility}</td>
                    <td className={styles.td}>
                      <span className={repo.active ? styles.on : styles.off}>
                        {repo.active ? 'Active' : 'Paused'}
                      </span>
                    </td>
                    <td className={`${styles.td} ${styles.right} ${styles.date}`}>
                      {repo.updated}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card flush>
        <div className={styles.tableHead}>
          <h2 className={styles.tableTitle}>Recent reviews</h2>
        </div>
        {user.recentReviews.length === 0 ? (
          <div className={styles.empty}>No review recorded for this user yet.</div>
        ) : (
          <div className={styles.scroll}>
            <table className={styles.table}>
              <thead>
                <tr className={styles.headRow}>
                  <th className={styles.th}>Repository</th>
                  <th className={styles.th}>Pull request</th>
                  <th className={styles.th}>Score</th>
                  <th className={styles.th}>Status</th>
                  <th className={`${styles.th} ${styles.right}`}>Reviewed</th>
                </tr>
              </thead>
              <tbody>
                {user.recentReviews.map((rv) => (
                  <tr key={`${rv.repo}-${rv.number}`} className={styles.staticRow}>
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
                    <td className={`${styles.td} ${styles.right} ${styles.date}`}>
                      {rv.reviewedAt}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}

/**
 * One account, in full. The support view: it answers "why is PRLens not reviewing
 * this person's repo" without anybody opening a psql session.
 *
 * Read-only, like the rest of the admin section — it reports on the user's repos,
 * it cannot disconnect or reconfigure them.
 */
export function AdminUserPage() {
  const { id } = useParams<{ id: string }>()
  const userId = Number(id)
  const user = useAsync(() => api.getAdminUser(userId), [userId])

  return (
    <div className={styles.container}>
      <Link to="/admin" className={styles.back}>
        <Icon name="arrow-right" size={14} className={styles.backIcon} /> All users
      </Link>

      <AsyncBoundary state={user} minHeight={320}>
        {(data) => <Detail user={data} />}
      </AsyncBoundary>
    </div>
  )
}
