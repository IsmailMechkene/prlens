import { Link } from 'react-router-dom'
import styles from './Footer.module.css'

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.brand}>
        <img src="/prlens_logo.png" alt="" className={styles.mark} />
        <span className={styles.name}>PRLens</span>
        <span className={styles.sep}>·</span>
        <span>© 2026</span>
      </div>
      <div className={styles.links}>
        <Link to="/privacy" className={styles.link}>Privacy</Link>
        <Link to="/terms" className={styles.link}>Terms</Link>
        <span className={styles.link}>Status</span>
        <span className={styles.link}>GitHub</span>
      </div>
    </footer>
  )
}
