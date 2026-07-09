import { Icon } from '../ui/Icon'
import styles from './Footer.module.css'

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.brand}>
        <Icon name="scan-eye" size={16} color="var(--pa)" />
        <span className={styles.name}>PRLens</span>
        <span className={styles.sep}>·</span>
        <span>© 2026</span>
      </div>
      <div className={styles.links}>
        <span className={styles.link}>Privacy</span>
        <span className={styles.link}>Terms</span>
        <span className={styles.link}>Status</span>
        <span className={styles.link}>GitHub</span>
      </div>
    </footer>
  )
}
