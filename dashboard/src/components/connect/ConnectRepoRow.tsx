import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../lib/api'
import type { GitHubRepo } from '../../lib/types'
import { Icon } from '../ui/Icon'
import styles from './ConnectRepoRow.module.css'

interface ConnectRepoRowProps {
  repo: GitHubRepo
  onEnabled: () => void
}

export function ConnectRepoRow({ repo, onEnabled }: ConnectRepoRowProps) {
  const navigate = useNavigate()
  const [enabling, setEnabling] = useState(false)

  // repo.name is the GitHub full_name ("acme/api-gateway"), so it must be encoded
  // to stay a single path segment under the /repos/:name route.
  const detailPath = `/repos/${encodeURIComponent(repo.name)}`

  const enable = async () => {
    setEnabling(true)
    try {
      await api.enableRepo(repo.name, repo.owner, repo.visibility)
      onEnabled()
      navigate(detailPath)
    } finally {
      setEnabling(false)
    }
  }

  return (
    <div className={styles.row}>
      <Icon name={repo.visibility === 'Public' ? 'book' : 'lock'} size={17} className={styles.icon} />
      <div className={styles.meta}>
        <div className={styles.nameRow}>
          <span className={styles.name}>{repo.name}</span>
          <span className={styles.visibility}>{repo.visibility}</span>
        </div>
        <div className={styles.updated}>Updated {repo.updated}</div>
      </div>

      {repo.connected ? (
        <div className={styles.configured}>
          <span className={styles.configuredLabel}>
            <Icon name="circle-check-big" size={15} /> Configured
          </span>
          <button
            type="button"
            className={styles.settingsLink}
            onClick={() => navigate(detailPath)}
          >
            Settings
          </button>
        </div>
      ) : (
        <button type="button" className={styles.enable} onClick={enable} disabled={enabling}>
          <Icon name="zap" size={14} /> {enabling ? 'Enabling…' : 'Enable PRLens'}
        </button>
      )}
    </div>
  )
}
