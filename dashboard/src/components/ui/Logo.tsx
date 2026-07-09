import styles from './Logo.module.css'

interface LogoProps {
  /** Badge edge length in px. */
  size?: number
  /** Show the "PRLens" wordmark next to the badge. */
  withWordmark?: boolean
  /** Ring around the badge (used on dark hero surfaces). */
  ring?: boolean
}

export function Logo({ size = 30, withWordmark = true, ring = true }: LogoProps) {
  return (
    <span className={styles.logo}>
      <img
        src="/prlens_logo.png"
        alt="PRLens"
        className={styles.badge}
        style={{
          width: size,
          height: size,
          boxShadow: ring ? '0 0 0 1px var(--pa-t40)' : 'none',
        }}
      />
      {withWordmark && <span className={styles.word}>PRLens</span>}
    </span>
  )
}
