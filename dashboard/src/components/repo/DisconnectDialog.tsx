import { useState } from 'react'
import { api } from '../../lib/api'
import { Button } from '../ui/Button'
import { Icon } from '../ui/Icon'
import { Modal } from '../ui/Modal'
import styles from './DisconnectDialog.module.css'

interface DisconnectDialogProps {
  /** GitHub full_name of the repo to remove, e.g. "acme/api-gateway". */
  repo: string
  open: boolean
  /** Dismissed without disconnecting. */
  onCancel: () => void
  /** The repo is gone. The caller decides where to go next. */
  onDone: () => void
}

type Stage = 'confirm' | 'working' | 'detached' | 'failed'

/**
 * Confirm-and-disconnect flow for a repo, in one dialog.
 *
 * It owns the request as well as the confirmation, because the outcome has three
 * shapes and two of them need saying: the rows and the GitHub App attachment both
 * went; the rows went but GitHub would not let go, so the repo may still be
 * reviewed; or the whole thing failed. Only the first is safe to close silently.
 */
export function DisconnectDialog({ repo, open, onCancel, onDone }: DisconnectDialogProps) {
  const [stage, setStage] = useState<Stage>('confirm')

  const close = () => {
    if (stage === 'working') return // a request is in flight; don't strand it
    if (stage === 'confirm' || stage === 'failed') {
      setStage('confirm')
      onCancel()
      return
    }
    onDone() // 'detached': the repo is gone, whatever GitHub did
  }

  const disconnect = async () => {
    setStage('working')
    try {
      const result = await api.disconnectRepo(repo)
      // Removed here either way — but if GitHub kept the repo attached to the App it
      // can still be sent for review, and the user has to hear that.
      if (result.githubRemoved) {
        onDone()
      } else {
        setStage('detached')
      }
    } catch {
      setStage('failed')
    }
  }

  return (
    <Modal open={open} onClose={close} title={`Disconnect ${repo}`}>
      {stage === 'detached' ? (
        <>
          <div className={styles.head}>
            <span className={`${styles.badge} ${styles.badgeWarn}`}>
              <Icon name="circle-alert" size={17} />
            </span>
            <h2 className={styles.title}>Removed, but still on GitHub</h2>
          </div>
          <p className={styles.body}>
            <span className={styles.repo}>{repo}</span> was removed from PRLens, but it could
            not be detached from the PRLens GitHub App — so GitHub may keep sending its pull
            requests for review.
          </p>
          <p className={styles.body}>
            Remove it yourself under <strong>GitHub → Settings → Applications → PRLens →
            Configure</strong>.
          </p>
          <div className={styles.actions}>
            <Button variant="primary" onClick={onDone}>
              Got it
            </Button>
          </div>
        </>
      ) : (
        <>
          <div className={styles.head}>
            <span className={`${styles.badge} ${styles.badgeDanger}`}>
              <Icon name="trash-2" size={16} />
            </span>
            <h2 className={styles.title}>Disconnect repository</h2>
          </div>

          <p className={styles.body}>
            This removes PRLens from <span className={styles.repo}>{repo}</span> entirely. Its
            review history, issue stats and settings are deleted, and the repository is
            detached from the PRLens GitHub App so it stops being reviewed.
          </p>
          <p className={styles.warning}>
            <Icon name="circle-alert" size={13} /> This cannot be undone. You can reconnect the
            repo later, but its history is gone.
          </p>

          {stage === 'failed' && (
            <p className={styles.error} role="alert">
              <Icon name="circle-alert" size={13} /> Couldn’t disconnect — nothing was changed.
              Try again.
            </p>
          )}

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.cancel}
              onClick={close}
              disabled={stage === 'working'}
            >
              Cancel
            </button>
            <button
              type="button"
              className={styles.confirm}
              onClick={disconnect}
              disabled={stage === 'working'}
            >
              {stage === 'working' ? 'Removing…' : 'Disconnect repository'}
            </button>
          </div>
        </>
      )}
    </Modal>
  )
}
