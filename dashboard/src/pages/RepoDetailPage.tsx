import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAsync } from '../lib/useAsync'
import type { AsyncState } from '../lib/useAsync'
import { issueColor } from '../lib/reviewStyles'
import type { RepoDetail, Review } from '../lib/types'
import { Card } from '../components/ui/Card'
import { Icon } from '../components/ui/Icon'
import { Skeleton } from '../components/ui/Skeleton'
import { Toggle } from '../components/ui/Toggle'
import { GitHubIcon } from '../components/ui/GitHubIcon'
import { AsyncBoundary } from '../components/ui/AsyncBoundary'
import { QualityTrendChart } from '../components/repo/QualityTrendChart'
import { IssuesDonut } from '../components/repo/IssuesDonut'
import { RecentReviews } from '../components/repo/RecentReviews'
import { ReviewSettings } from '../components/repo/ReviewSettings'
import { DisconnectDialog } from '../components/repo/DisconnectDialog'
import styles from './RepoDetailPage.module.css'

const detailSkeleton = (
  <>
    <div className={styles.headSkeleton}>
      <div className={styles.headSkeletonText}>
        <Skeleton width={260} height={22} />
        <Skeleton width={380} height={13} />
      </div>
      <Skeleton width={150} height={32} radius={8} />
    </div>
    <div className={styles.charts}>
      {[0, 1].map((i) => (
        <Card key={i} className={styles.chartCard}>
          <Skeleton width={150} height={14} />
          <Skeleton height={132} radius={10} style={{ marginTop: 20 }} />
        </Card>
      ))}
    </div>
  </>
)

const reviewsSkeleton = (
  <div>
    {[0, 1, 2, 3].map((i) => (
      <div key={i} className={styles.reviewSkeleton}>
        <Skeleton width="46%" height={13} />
        <Skeleton width={44} height={20} radius={6} />
      </div>
    ))}
  </div>
)

/** Quality is up, down, or flat since the start of the window. */
function deltaArrow(delta: number): string {
  if (delta > 0) return '▲'
  if (delta < 0) return '▼'
  return '–'
}

function deltaColor(delta: number): string {
  if (delta > 0) return 'var(--success)'
  if (delta < 0) return 'var(--danger)'
  return 'var(--fg-muted)'
}

export function RepoDetailPage() {
  const { name = '' } = useParams()
  const repo = useAsync(() => api.getRepo(name), [name])
  const reviews = useAsync(() => api.getRepoReviews(name), [name])

  return (
    <div className={styles.container}>
      <div className={styles.breadcrumb}>
        <Link to="/dashboard" className={styles.crumbLink}>
          Dashboard
        </Link>
        <Icon name="chevron-right" size={13} />
        <span className={styles.crumbCurrent}>{name}</span>
      </div>

      <AsyncBoundary state={repo} minHeight={400} skeleton={detailSkeleton}>
        {/*
          Keyed by repo: navigating from one repo to another keeps this subtree
          mounted (useAsync holds the previous data while refetching), so without a
          key the `useState(initial)` seeds below — the active toggle and the whole
          settings form — would keep the *previous* repo's values, and saving would
          write them onto this one.
        */}
        {(data) => <RepoDetailContent key={data.name} detail={data} reviews={reviews} />}
      </AsyncBoundary>
    </div>
  )
}

function RepoDetailContent({
  detail,
  reviews,
}: {
  detail: RepoDetail
  reviews: AsyncState<Review[]>
}) {
  const navigate = useNavigate()
  const [active, setActive] = useState(detail.active)
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false)
  const totalIssues = detail.issues.reduce((s, i) => s + i.value, 0)

  // The backend sends GitHub's full_name ("acme/api-gateway") as `name`, so
  // prefixing it with the owner again yields "acme/acme/api-gateway" — and a
  // GitHub link that 404s. The mock fixtures use the short name, hence the check.
  const fullName = detail.name.includes('/') ? detail.name : `${detail.owner}/${detail.name}`

  const onToggle = async (next: boolean) => {
    setActive(next)
    try {
      await api.setRepoActive(detail.name, next)
    } catch {
      setActive(!next) // revert on failure
    }
  }

  return (
    <>
      <DisconnectDialog
        repo={detail.name}
        open={confirmingDisconnect}
        onCancel={() => setConfirmingDisconnect(false)}
        onDone={() => {
          // The repo no longer exists as far as the app is concerned, so this page
          // cannot stay: `replace` keeps Back from returning to a dead route.
          navigate('/connect', { replace: true })
        }}
      />
      {/* Header */}
      <div className={styles.header}>
        <div>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>{fullName}</h1>
            <span className={styles.visibility}>{detail.visibility}</span>
          </div>
          <p className={styles.desc}>{detail.description}</p>
        </div>
        <div className={styles.headerActions}>
          <a
            className={styles.ghLink}
            href={`https://github.com/${fullName}`}
            target="_blank"
            rel="noreferrer"
          >
            <GitHubIcon size={15} /> Open on GitHub
          </a>
          <button
            type="button"
            className={styles.disconnect}
            onClick={() => setConfirmingDisconnect(true)}
          >
            <Icon name="trash-2" size={14} /> Disconnect
          </button>
          <div className={styles.toggleBox}>
            <span
              className={styles.toggleLabel}
              style={{ color: active ? 'var(--success)' : 'var(--fg-muted)' }}
            >
              {active ? 'Active' : 'Inactive'}
            </span>
            <Toggle checked={active} onChange={onToggle} label="PRLens active" />
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className={styles.charts}>
        <Card className={styles.chartCard}>
          <div className={styles.chartHead}>
            <h3 className={styles.chartTitle}>Quality score trend</h3>
            <span className={styles.chartMeta}>Last 30 days</span>
          </div>
          <div className={styles.scoreRow}>
            <span className={styles.score}>{detail.currentScore}</span>
            {/* The arrow used to be a hard-coded ▲, so a repo whose quality had
                fallen still read "▲ -4 pts". */}
            <span
              className={styles.scoreDelta}
              style={{ color: deltaColor(detail.scoreDelta) }}
            >
              {deltaArrow(detail.scoreDelta)} {Math.abs(detail.scoreDelta)} pts
            </span>
          </div>
          <QualityTrendChart data={detail.scoreTrend} />
        </Card>

        <Card className={styles.chartCard}>
          <h3 className={styles.chartTitle}>Issues breakdown</h3>
          <span className={styles.chartMeta}>{totalIssues} issues caught</span>
          <div className={styles.donutRow}>
            <IssuesDonut segments={detail.issues} />
            <div className={styles.legend}>
              {detail.issues.map((seg) => (
                <div key={seg.category} className={styles.legendItem}>
                  <span className={styles.legendDot} style={{ background: issueColor(seg.category) }} />
                  <span className={styles.legendLabel}>{seg.category}</span>
                  <span className={styles.legendVal}>{seg.value}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Reviews + settings */}
      <div className={styles.lower}>
        <Card flush>
          <div className={styles.panelHead}>
            <h3 className={styles.chartTitle}>Recent PR reviews</h3>
          </div>
          <AsyncBoundary state={reviews} minHeight={180} skeleton={reviewsSkeleton}>
            {(data) => <RecentReviews reviews={data} />}
          </AsyncBoundary>
        </Card>

        <Card flush>
          <div className={styles.panelHead}>
            <Icon name="sliders-horizontal" size={15} color="var(--fg-muted)" />
            <h3 className={styles.chartTitle}>Review settings</h3>
          </div>
          <ReviewSettings repo={detail.name} initial={detail.settings} />
        </Card>
      </div>
    </>
  )
}
