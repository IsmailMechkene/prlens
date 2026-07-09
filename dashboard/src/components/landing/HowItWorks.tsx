import { Icon } from '../ui/Icon'
import styles from './HowItWorks.module.css'

interface Step {
  num: string
  icon: string
  title: string
  desc: string
}

// Marketing copy — static, not backend-driven.
const STEPS: Step[] = [
  {
    num: '01',
    icon: 'circle-plus',
    title: 'Connect your repos',
    desc: 'Install the GitHub App and pick repositories. No CI config, no YAML, nothing to maintain.',
  },
  {
    num: '02',
    icon: 'git-pull-request',
    title: 'Open a pull request',
    desc: 'PRLens picks up every new PR and every push automatically — nothing changes in your workflow.',
  },
  {
    num: '03',
    icon: 'scan-eye',
    title: 'Get the review',
    desc: 'Inline comments, a quality score and labels land right on the PR, seconds after it opens.',
  },
]

export function HowItWorks() {
  return (
    <section className={styles.section}>
      <div className={styles.head}>
        <div className={styles.eyebrow}>How it works</div>
        <h2 className={styles.heading}>Live in under a minute</h2>
      </div>
      <div className={styles.steps}>
        <div className={styles.rail} aria-hidden="true" />
        {STEPS.map((s) => (
          <div key={s.num} className={styles.step}>
            <div className={styles.marker}>
              <Icon name={s.icon} size={19} />
            </div>
            <div className={styles.num}>{s.num}</div>
            <h3 className={styles.stepTitle}>{s.title}</h3>
            <p className={styles.stepDesc}>{s.desc}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
