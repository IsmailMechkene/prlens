import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '../ui/Icon'
import { GitHubIcon } from '../ui/GitHubIcon'
import { Button } from '../ui/Button'
import { DemoModal } from './DemoModal'
import styles from './CtaBand.module.css'

/** Closing call-to-action panel before the footer. */
export function CtaBand() {
  const navigate = useNavigate()
  const [demoOpen, setDemoOpen] = useState(false)
  return (
    <section className={styles.section}>
      <div className={styles.card}>
        <div className={styles.glow} aria-hidden="true" />
        <h2 className={styles.heading}>
          Your next PR deserves a<br />
          <span className={styles.gradient}>second pair of eyes</span>
        </h2>
        <p className={styles.sub}>
          Install PRLens in under a minute — the first review lands on your very next pull request.
        </p>
        <div className={styles.actions}>
          <Button variant="primary" size="lg" onClick={() => navigate('/dashboard')}>
            <GitHubIcon size={18} /> Get started free
          </Button>
          <Button variant="secondary" size="lg" onClick={() => setDemoOpen(true)}>
            <Icon name="play" size={16} /> Watch demo
          </Button>
        </div>
        <div className={styles.fineprint}>Free for open source · No credit card required</div>
      </div>

      <DemoModal open={demoOpen} onClose={() => setDemoOpen(false)} />
    </section>
  )
}
