import { useNavigate } from 'react-router-dom'
import type { Review } from '../../lib/types'
import { Icon } from '../ui/Icon'
import { ScoreBadge } from '../ui/ScoreBadge'
import { StatusBadge } from '../ui/StatusBadge'
import styles from './ReviewsTable.module.css'

export function ReviewsTable({ reviews }: { reviews: Review[] }) {
  const navigate = useNavigate()
  return (
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
          {reviews.map((rv) => (
            <tr
              key={`${rv.repo}-${rv.number}`}
              className={styles.row}
              onClick={() => navigate(`/repos/${encodeURIComponent(rv.repo)}`)}
            >
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
