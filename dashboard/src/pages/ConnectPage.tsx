import { useMemo, useState } from 'react'
import { api } from '../lib/api'
import { useAsync } from '../lib/useAsync'
import { Card } from '../components/ui/Card'
import { Icon } from '../components/ui/Icon'
import { AsyncBoundary } from '../components/ui/AsyncBoundary'
import { Skeleton } from '../components/ui/Skeleton'
import { ConnectRepoRow } from '../components/connect/ConnectRepoRow'
import styles from './ConnectPage.module.css'

const reposSkeleton = (
  <div>
    {[0, 1, 2, 3, 4, 5].map((i) => (
      <div key={i} className={styles.rowSkeleton}>
        <Skeleton width={17} height={17} radius={4} />
        <div className={styles.rowSkeletonMeta}>
          <Skeleton width="42%" height={13} />
          <Skeleton width="22%" height={11} />
        </div>
        <Skeleton width={104} height={30} radius={8} />
      </div>
    ))}
  </div>
)

export function ConnectPage() {
  const [search, setSearch] = useState('')
  // Lists everything on GitHub, not just repos PRLens already knows about,
  // so a brand-new repo can be enabled from here.
  const repos = useAsync(() => api.getGitHubRepos(), [])

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return (repos.data ?? [])
      .filter((r) => r.name.toLowerCase().includes(q))
      // Connected repos first: those are the ones with something to manage. Sort is
      // stable, so GitHub's own ordering (most recently updated) survives inside
      // each group.
      .sort((a, b) => Number(b.connected) - Number(a.connected))
  }, [repos.data, search])

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Connect a repository</h1>
      <p className={styles.subtitle}>
        Enable PRLens on repositories in <span className={styles.org}>acme-inc</span>. It will start
        reviewing new pull requests immediately.
      </p>

      <div className={styles.search}>
        <Icon name="search" size={16} color="var(--fg-subtle)" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter repositories…"
          className={styles.searchInput}
        />
        <span className={styles.count}>{filtered.length} repos</span>
      </div>

      <Card flush>
        <AsyncBoundary state={repos} minHeight={200} skeleton={reposSkeleton}>
          {() =>
            filtered.length ? (
              filtered.map((repo) => (
                <ConnectRepoRow key={repo.name} repo={repo} onChanged={repos.reload} />
              ))
            ) : (
              <div className={styles.empty}>No repositories match “{search}”.</div>
            )
          }
        </AsyncBoundary>
      </Card>
    </div>
  )
}
