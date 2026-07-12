import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync } from '../lib/useAsync'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Icon } from '../components/ui/Icon'
import { AsyncBoundary } from '../components/ui/AsyncBoundary'
import { Skeleton } from '../components/ui/Skeleton'
import { PageHeader } from '../components/layout/PageHeader'
import { StatCard } from '../components/dashboard/StatCard'
import { ReviewsTable } from '../components/dashboard/ReviewsTable'
import styles from './DashboardPage.module.css'

/**
 * One placeholder per stat tile — four, matching the four the endpoint returns and
 * the four columns of the grid. The Card primitive carries no padding of its own
 * (StatCard adds it), so the skeleton has to supply its own, or its contents sit
 * flush against the border.
 */
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

const reviewsSkeleton = (
  <div>
    {[0, 1, 2, 3, 4].map((i) => (
      <div key={i} className={styles.rowSkeleton}>
        <Skeleton width="20%" />
        <Skeleton width="34%" />
        <Skeleton width="8%" />
        <Skeleton width="14%" />
        <Skeleton width="9%" />
      </div>
    ))}
  </div>
)

export function DashboardPage() {
  const navigate = useNavigate()
  const stats = useAsync(() => api.getDashboardStats(), [])
  const reviews = useAsync(() => api.getReviews(), [])

  return (
    <div className={styles.container}>
      <PageHeader
        title="Dashboard"
        subtitle="Overview of PRLens activity across your repositories."
        action={
          <Button variant="primary" onClick={() => navigate('/connect')}>
            <Icon name="plus" size={16} /> Connect new repo
          </Button>
        }
      />

      <div className={styles.stats}>
        <AsyncBoundary state={stats} minHeight={92} skeleton={statsSkeleton}>
          {(data) => data.stats.map((s) => <StatCard key={s.id} stat={s} />)}
        </AsyncBoundary>
      </div>

      <Card flush>
        <div className={styles.tableHead}>
          <h2 className={styles.tableTitle}>Recent reviews</h2>
          <span className={styles.viewAll}>View all</span>
        </div>
        <AsyncBoundary state={reviews} minHeight={160} skeleton={reviewsSkeleton}>
          {(data) => <ReviewsTable reviews={data} />}
        </AsyncBoundary>
      </Card>
    </div>
  )
}
