import { useNavigate } from 'react-router-dom'
import { Icon } from '../ui/Icon'
import { GitHubIcon } from '../ui/GitHubIcon'
import { Button } from '../ui/Button'
import styles from './Hero.module.css'

export function Hero() {
  const navigate = useNavigate()
  return (
    <header className={styles.hero}>
      <div className={styles.pill}>
        <span className={styles.live}>
          <span className={styles.liveDot} /> Live
        </span>
        <span className={styles.sep}>|</span>
        Now reviewing on 12,000+ repositories
      </div>

      <h1 className={styles.title}>
        AI Code Review
        <br />
        for <span className={styles.gradient}>GitHub</span>
      </h1>

      <p className={styles.subtitle}>
        PRLens reviews every pull request the moment it opens — flagging security holes, scoring
        quality, and labeling changes automatically, so your team ships with confidence.
      </p>

      <div className={styles.actions}>
        <Button variant="primary" size="lg" onClick={() => navigate('/dashboard')}>
          <GitHubIcon size={18} /> Login with GitHub
        </Button>
        <Button variant="secondary" size="lg" onClick={() => navigate('/dashboard')}>
          View demo <Icon name="arrow-right" size={16} />
        </Button>
      </div>

      <div className={styles.fineprint}>Free for open source · No credit card required</div>
    </header>
  )
}
