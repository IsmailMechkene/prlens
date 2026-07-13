import { Link, useNavigate } from 'react-router-dom'
import { Logo } from '../ui/Logo'
import { GitHubIcon } from '../ui/GitHubIcon'
import styles from './Navbar.module.css'

export function Navbar() {
  const navigate = useNavigate()
  return (
    <div className={styles.bar}>
      <nav className={styles.nav}>
        <Logo size={30} />
        <div className={styles.links}>
          <Link to="/features" className={styles.link}>Features</Link>
          <Link to="/docs" className={styles.link}>Docs</Link>
          <button type="button" className={styles.signIn} onClick={() => navigate('/dashboard')}>
            <GitHubIcon size={15} /> Sign in
          </button>
        </div>
      </nav>
    </div>
  )
}
