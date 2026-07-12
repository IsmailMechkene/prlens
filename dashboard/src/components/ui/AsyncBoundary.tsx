import type { ReactNode } from 'react'
import { Icon } from './Icon'
import styles from './AsyncBoundary.module.css'

interface AsyncBoundaryProps<T> {
  state: { data: T | undefined; loading: boolean; error: Error | undefined; reload: () => void }
  children: (data: T) => ReactNode
  /** Optional inline height so panels don't collapse while loading. */
  minHeight?: number
  /**
   * Placeholder shown on the first load instead of the spinner. Pass one wherever
   * the shape of the content is known in advance — it holds the layout in place, so
   * the page doesn't reflow when the data arrives.
   */
  skeleton?: ReactNode
}

/** Renders loading / error / content branches for a useAsync state. */
export function AsyncBoundary<T>({
  state,
  children,
  minHeight = 120,
  skeleton,
}: AsyncBoundaryProps<T>) {
  if (state.loading && state.data === undefined) {
    if (skeleton) {
      // `display: contents` so the placeholders become children of whatever laid the
      // real content out — the dashboard's stats grid, for one — instead of all
      // landing in a single cell of it.
      return (
        <div className={styles.skeletonHost} aria-busy="true" aria-label="Loading">
          {skeleton}
        </div>
      )
    }
    return (
      <div className={styles.center} style={{ minHeight }}>
        <span className={styles.spinner} aria-label="Loading" />
      </div>
    )
  }
  if (state.error) {
    return (
      <div className={styles.center} style={{ minHeight }}>
        <div className={styles.error}>
          <Icon name="circle-alert" size={18} />
          <span>Couldn’t load data.</span>
          <button type="button" className={styles.retry} onClick={state.reload}>
            Retry
          </button>
        </div>
      </div>
    )
  }
  if (state.data === undefined) return null
  return <>{children(state.data)}</>
}
