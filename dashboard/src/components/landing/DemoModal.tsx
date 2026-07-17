import { Icon } from '../ui/Icon'
import { Modal } from '../ui/Modal'
import styles from './DemoModal.module.css'

interface DemoModalProps {
  open: boolean
  onClose: () => void
}

/**
 * Plays the recorded product demo.
 *
 * The file is ~34 MB, so it must not land on every visitor who never asks for it:
 * Modal renders nothing while closed, so the <video> — and its download — only
 * comes into existence once someone actually opens the demo.
 */
export function DemoModal({ open, onClose }: DemoModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="PRLens demo" size="wide">
      <div className={styles.head}>
        <h2 className={styles.title}>PRLens in action</h2>
        <button type="button" className={styles.close} onClick={onClose} aria-label="Close demo">
          <Icon name="x" size={18} />
        </button>
      </div>

      {/* autoPlay is a hint, not a guarantee — Safari and Firefox may refuse it for
          audio, which is why the native controls are always present as the fallback. */}
      <video className={styles.video} src="/prlens_demo.mp4" controls autoPlay playsInline>
        Your browser cannot play this video.{' '}
        <a href="/prlens_demo.mp4" download>
          Download it instead
        </a>
        .
      </video>
    </Modal>
  )
}
