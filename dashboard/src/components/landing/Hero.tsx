import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '../ui/Icon'
import { GitHubIcon } from '../ui/GitHubIcon'
import { Button } from '../ui/Button'
import { DemoModal } from './DemoModal'
import styles from './Hero.module.css'

export function Hero() {
  const navigate = useNavigate()
  const [demoOpen, setDemoOpen] = useState(false)
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
        <span className={styles.primaryGlow}>
          <Button variant="primary" size="lg" onClick={() => navigate('/dashboard')}>
            <GitHubIcon size={18} /> Login with GitHub
          </Button>
        </span>
        <Button variant="secondary" size="lg" onClick={() => setDemoOpen(true)}>
          <Icon name="play" size={16} /> Watch demo
        </Button>
      </div>

      <div className={styles.fineprint}>Free for open source · No credit card required</div>

      <DemoModal open={demoOpen} onClose={() => setDemoOpen(false)} />
    </header>
  )
}
