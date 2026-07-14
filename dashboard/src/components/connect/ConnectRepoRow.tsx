import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../lib/api'
import type { GitHubRepo } from '../../lib/types'
import { Icon } from '../ui/Icon'
import { DisconnectDialog } from '../repo/DisconnectDialog'
import styles from './ConnectRepoRow.module.css'

interface ConnectRepoRowProps {
  repo: GitHubRepo
  /** Re-fetch the list: the row's connected state has changed. */
  onChanged: () => void
}

export function ConnectRepoRow({ repo, onChanged }: ConnectRepoRowProps) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [confirming, setConfirming] = useState(false)

  // repo.name is the GitHub full_name ("acme/api-gateway"). The /repos/* route
  // takes the slash as-is, so the name goes in the path unencoded.
  const detailPath = `/repos/${repo.name}`

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

  return (
    <div className={styles.row}>
      <DisconnectDialog
        repo={repo.name}
        open={confirming}
        onCancel={() => setConfirming(false)}
        onDone={() => {
          setConfirming(false)
          onChanged()
        }}
      />
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
            onClick={() => setConfirming(true)}
            disabled={busy}
          >
            Disconnect
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
