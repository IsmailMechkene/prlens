import { useNavigate } from 'react-router-dom'
import type { Review } from '../../lib/types'
import { ScoreBadge } from '../ui/ScoreBadge'
import { StatusBadge } from '../ui/StatusBadge'
import styles from './RecentReviews.module.css'

export function RecentReviews({ reviews }: { reviews: Review[] }) {
  const navigate = useNavigate()
  return (
    <div>
      {reviews.map((rv) => (
        <button
          type="button"
          key={`${rv.repo}-${rv.number}`}
          className={styles.row}
          onClick={() => navigate(`/repos/${encodeURIComponent(rv.repo)}`)}
        >
          <ScoreBadge score={rv.score} />
          <div className={styles.meta}>
            <div className={styles.title}>
              <span className={styles.num}>#{rv.number}</span>
              {rv.title}
            </div>
            <div className={styles.date}>{rv.reviewedAt}</div>
          </div>
          <StatusBadge status={rv.status} iconOnly />
        </button>
      ))}
    </div>
  )
}
