import type { HTMLAttributes } from 'react'
import styles from './Card.module.css'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Clip children to the rounded corners (for tables / lists). */
  flush?: boolean
}

/** Bordered surface used for every panel in the app. */
export function Card({ flush, className, ...rest }: CardProps) {
  const cls = [styles.card, flush && styles.flush, className].filter(Boolean).join(' ')
  return <div className={cls} {...rest} />
}
