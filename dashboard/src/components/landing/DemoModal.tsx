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
 * Modal renders nothing while closed, so the <video> — and its download — only
 * comes into existence once someone actually opens the demo, rather than on every
 * visit from someone who never asks for it.
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

      {/* The recording has no audio track at all, so `muted` costs the viewer nothing
          and buys reliable autoplay: browsers block autoplay *with sound*, and without
          this they would show a dead first frame until the user hit play. */}
      <video className={styles.video} src="/prlens_demo.mp4" controls autoPlay muted playsInline>
        Your browser cannot play this video.{' '}
        <a href="/prlens_demo.mp4" download>
          Download it instead
        </a>
        .
      </video>
    </Modal>
  )
}
