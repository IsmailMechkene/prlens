import { logout } from '../../lib/api'
import { Icon } from '../ui/Icon'
import { Modal } from '../ui/Modal'
import styles from './LogoutDialog.module.css'

interface LogoutDialogProps {
  open: boolean
  onCancel: () => void
}

/** Confirm-and-log-out prompt for the sidebar's disconnect button. */
export function LogoutDialog({ open, onCancel }: LogoutDialogProps) {
  const confirm = () => {
    logout()
    window.location.href = '/'
  }

  return (
    <Modal open={open} onClose={onCancel} title="Log out">
      <div className={styles.head}>
        <span className={styles.badge}>
          <Icon name="log-out" size={16} />
        </span>
        <h2 className={styles.title}>Log out of PRLens</h2>
      </div>

      <p className={styles.body}>
        You’ll be signed out of this browser and returned to the landing page. You can sign back
        in with GitHub at any time.
      </p>

      <div className={styles.actions}>
        <button type="button" className={styles.cancel} onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className={styles.confirm} onClick={confirm}>
          Log out
        </button>
      </div>
    </Modal>
  )
}
