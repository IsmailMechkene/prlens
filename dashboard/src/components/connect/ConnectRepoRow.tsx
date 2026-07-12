import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../lib/api'
import { confirmDisconnect, reportDisconnect } from '../../lib/disconnect'
import type { GitHubRepo } from '../../lib/types'
import { Icon } from '../ui/Icon'
import styles from './ConnectRepoRow.module.css'

interface ConnectRepoRowProps {
  repo: GitHubRepo
  /** Re-fetch the list: the row's connected state has changed. */
  onChanged: () => void
}

export function ConnectRepoRow({ repo, onChanged }: ConnectRepoRowProps) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)

  // repo.name is the GitHub full_name ("acme/api-gateway"), so it must be encoded
  // to stay a single path segment under the /repos/:name route.
  const detailPath = `/repos/${encodeURIComponent(repo.name)}`

  const enable = async () => {
    setBusy(true)
    try {
      await api.enableRepo(repo.name, repo.owner, repo.visibility)
      onChanged()
      navigate(detailPath)
    } finally {
      setBusy(false)
    }
  }

  const disconnect = async () => {
    if (!confirmDisconnect(repo.name)) return
    setBusy(true)
    try {
      reportDisconnect(repo.name, await api.disconnectRepo(repo.name))
      onChanged()
    } finally {
      setBusy(false)
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
          <button
            type="button"
            className={styles.disconnect}
            onClick={disconnect}
            disabled={busy}
          >
            {busy ? 'Removing…' : 'Disconnect'}
          </button>
        </div>
      ) : (
        <button type="button" className={styles.enable} onClick={enable} disabled={busy}>
          <Icon name="zap" size={14} /> {busy ? 'Enabling…' : 'Enable PRLens'}
        </button>
      )}
    </div>
  )
}
