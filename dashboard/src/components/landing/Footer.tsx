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
        <Link to="/status" className={styles.link}>Status</Link>
        <a
          href="https://github.com/IsmailMechkene/prlens"
          className={styles.link}
          target="_blank"
          rel="noreferrer"
        >
          GitHub
        </a>
      </div>
    </footer>
  )
}
