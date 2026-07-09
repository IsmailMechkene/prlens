import { statusMeta } from '../../lib/reviewStyles'
import type { ReviewStatus } from '../../lib/types'
import { Icon } from './Icon'
import styles from './StatusBadge.module.css'

interface StatusBadgeProps {
  status: ReviewStatus
  /** Render only the icon (used in compact lists). */
  iconOnly?: boolean
}

export function StatusBadge({ status, iconOnly }: StatusBadgeProps) {
  const meta = statusMeta(status)
  if (iconOnly) {
    return (
      <span className={styles.iconOnly} style={{ color: meta.color }} title={meta.label}>
        <Icon name={meta.icon} size={16} />
      </span>
    )
  }
  return (
    <span className={styles.badge} style={{ color: meta.color }}>
      <Icon name={meta.icon} size={14} />
      {meta.label}
    </span>
  )
}
