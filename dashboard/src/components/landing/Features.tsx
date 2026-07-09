import { Icon } from '../ui/Icon'
import { Card } from '../ui/Card'
import styles from './Features.module.css'

interface Feature {
  icon: string
  color: string
  tint: string
  title: string
  desc: string
}

// Marketing copy — static, not backend-driven.
const FEATURES: Feature[] = [
  {
    icon: 'shield-alert',
    color: 'var(--danger)',
    tint: 'rgba(248,81,73,0.12)',
    title: 'Security detection',
    desc: 'Catches injection, auth flaws, secret leaks and unsafe dependencies before they merge — with CWE references.',
  },
  {
    icon: 'gauge',
    color: 'var(--success)',
    tint: 'rgba(63,185,80,0.12)',
    title: 'Quality scoring',
    desc: 'Every PR gets a 0–100 score across complexity, tests and maintainability, trended over time per repo.',
  },
  {
    icon: 'tags',
    color: 'var(--pa)',
    tint: 'var(--pa-t12)',
    title: 'Auto labels',
    desc: 'Applies labels and routes reviewers automatically from the diff — security, backend, needs-tests, and more.',
  },
  {
    icon: 'zap',
    color: 'var(--attention)',
    tint: 'rgba(210,153,34,0.12)',
    title: 'Reviews in seconds',
    desc: 'Feedback arrives while the diff is still fresh in your head — a median of 4.2 seconds after the PR opens.',
  },
  {
    icon: 'git-pull-request',
    color: 'var(--done)',
    tint: 'rgba(210,168,255,0.12)',
    title: 'Native to your workflow',
    desc: 'Reviews appear as ordinary PR comments and checks. No new tab, no new tool for your team to learn.',
  },
  {
    icon: 'sliders-horizontal',
    color: 'var(--pa-lite)',
    tint: 'var(--pa-t12)',
    title: 'Tuned per repository',
    desc: 'Set severity thresholds, focus areas and label rules per repo, so the review matches how each team works.',
  },
]

export function Features() {
  return (
    <section className={styles.section}>
      <div className={styles.head}>
        <div className={styles.eyebrow}>Every PR, reviewed</div>
        <h2 className={styles.heading}>Everything a great reviewer does</h2>
      </div>
      <div className={styles.grid}>
        {FEATURES.map((f) => (
          <Card key={f.title} className={styles.card}>
            <div className={styles.iconBox} style={{ background: f.tint, color: f.color }}>
              <Icon name={f.icon} size={21} />
            </div>
            <h3 className={styles.cardTitle}>{f.title}</h3>
            <p className={styles.cardDesc}>{f.desc}</p>
          </Card>
        ))}
      </div>
    </section>
  )
}
