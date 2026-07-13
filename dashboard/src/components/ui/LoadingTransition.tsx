import { useEffect, useRef, useState } from 'react'
import styles from './LoadingTransition.module.css'

const MESSAGES = [
  'Connecting to GitHub…',
  'Loading your repositories…',
  'Fetching review history…',
  'Almost ready…',
] as const

/** How long the progress bar takes to fill. Mirrored by --prl-intro-duration. */
const FILL_MS = 2600
/** Length of the closing fade. Must match the .leaving animation. */
const FADE_MS = 420
/** Dwell for the static reduced-motion branch, which has nothing to animate. */
const REDUCED_MS = 600

const MESSAGE_MS = FILL_MS / MESSAGES.length

interface LoadingTransitionProps {
  /** Called once the overlay has finished fading out and can be unmounted. */
  onComplete: () => void
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])
  return reduced
}

/**
 * Full-screen boot transition played over the app shell on a fresh login: the
 * lens badge pulses and scans while a progress bar fills, then the whole thing
 * fades out to reveal the dashboard already mounted underneath.
 *
 * Purely decorative — it runs on a fixed timeline rather than tracking real
 * request progress, and the caller is expected to have its data by the time it
 * ends. Nothing waits on it, so an early unmount costs nothing.
 */
export function LoadingTransition({ onComplete }: LoadingTransitionProps) {
  const reduced = usePrefersReducedMotion()
  const [message, setMessage] = useState(0)
  const [leaving, setLeaving] = useState(false)

  // Kept in a ref so a caller passing an inline arrow doesn't restart the run.
  const completeRef = useRef(onComplete)
  useEffect(() => {
    completeRef.current = onComplete
  }, [onComplete])

  useEffect(() => {
    const timers: number[] = []

    if (reduced) {
      timers.push(window.setTimeout(() => completeRef.current(), REDUCED_MS))
    } else {
      for (let i = 1; i < MESSAGES.length; i += 1) {
        timers.push(window.setTimeout(() => setMessage(i), i * MESSAGE_MS))
      }
      timers.push(window.setTimeout(() => setLeaving(true), FILL_MS))
      timers.push(window.setTimeout(() => completeRef.current(), FILL_MS + FADE_MS))
    }

    return () => timers.forEach(clearTimeout)
  }, [reduced])

  return (
    <div
      className={`${styles.overlay} ${leaving ? styles.leaving : ''}`}
      style={{ '--prl-intro-duration': `${FILL_MS}ms` } as React.CSSProperties}
      role="status"
      aria-live="polite"
      // The overlay is a splash, not content: the dashboard beneath it is the
      // real page, and it is already in the tree for a screen reader to walk.
      aria-label="Loading PRLens"
    >
      <div className={styles.lens}>
        <img src="/prlens_icon.svg" alt="" className={styles.mark} />
        <span className={styles.beam} />
        <span className={styles.halo} />
      </div>

      {!reduced && (
        <div className={styles.track}>
          <div className={styles.fill} />
        </div>
      )}

      <p className={styles.status}>
        {reduced ? (
          'Loading…'
        ) : (
          // Re-keying on the index restarts the entrance animation per message.
          <span key={message} className={styles.statusLine}>
            {MESSAGES[message]}
          </span>
        )}
      </p>
    </div>
  )
}
