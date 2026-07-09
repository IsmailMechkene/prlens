import { scoreStyle } from '../../lib/reviewStyles'
import styles from './ScoreBadge.module.css'

export function ScoreBadge({ score }: { score: number }) {
  const s = scoreStyle(score)
  return (
    <span
      className={styles.badge}
      style={{ color: s.color, background: s.bg, borderColor: s.border }}
    >
      {score}
    </span>
  )
}
