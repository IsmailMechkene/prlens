import { useMemo, useState } from 'react'
import { api } from '../lib/api'
import { useAsync } from '../lib/useAsync'
import { Card } from '../components/ui/Card'
import { Icon } from '../components/ui/Icon'
import { AsyncBoundary } from '../components/ui/AsyncBoundary'
import { ConnectRepoRow } from '../components/connect/ConnectRepoRow'
import styles from './ConnectPage.module.css'

export function ConnectPage() {
  const [search, setSearch] = useState('')
  const repos = useAsync(() => api.getRepos(), [])

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return (repos.data ?? []).filter((r) => r.name.toLowerCase().includes(q))
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
        <AsyncBoundary state={repos} minHeight={200}>
          {() =>
            filtered.length ? (
              filtered.map((repo) => (
                <ConnectRepoRow key={repo.name} repo={repo} onEnabled={repos.reload} />
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
