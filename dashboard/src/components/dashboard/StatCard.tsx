import { Icon } from '../ui/Icon'
import { Card } from '../ui/Card'
import type { Stat } from '../../lib/types'
import styles from './StatCard.module.css'

const TREND_COLOR: Record<Stat['trend'], string> = {
  up: 'var(--success)',
  down: 'var(--danger)',
  neutral: 'var(--fg-muted)',
}

export function StatCard({ stat }: { stat: Stat }) {
  return (
    <Card className={styles.card}>
      <div className={styles.label}>
        <Icon name={stat.icon} size={15} color={stat.iconColor} /> {stat.label}
      </div>
      <div className={styles.valueRow}>
        <span className={styles.value}>{stat.value}</span>
        <span className={styles.delta} style={{ color: TREND_COLOR[stat.trend] }}>
          {stat.delta}
        </span>
      </div>
    </Card>
  )
}
