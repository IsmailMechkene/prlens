import type { CSSProperties } from 'react'
import styles from './Skeleton.module.css'

interface SkeletonProps {
  width?: number | string
  height?: number | string
  radius?: number | string
  className?: string
  style?: CSSProperties
}

/**
 * A shimmering placeholder bar.
 *
 * Used instead of a spinner wherever the shape of the content is known before it
 * arrives — the panel then keeps its size and the layout doesn't jump when the
 * data lands. Purely decorative, so it is hidden from assistive tech; the
 * surrounding AsyncBoundary carries the busy state.
 */
export function Skeleton({
  width = '100%',
  height = 12,
  radius = 6,
  className,
  style,
}: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={className ? `${styles.bar} ${className}` : styles.bar}
      style={{ width, height, borderRadius: radius, ...style }}
    />
  )
}
