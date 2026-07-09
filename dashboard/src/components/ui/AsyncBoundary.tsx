import type { ReactNode } from 'react'
import { Icon } from './Icon'
import styles from './AsyncBoundary.module.css'

interface AsyncBoundaryProps<T> {
  state: { data: T | undefined; loading: boolean; error: Error | undefined; reload: () => void }
  children: (data: T) => ReactNode
  /** Optional inline height so panels don't collapse while loading. */
  minHeight?: number
}

/** Renders loading / error / content branches for a useAsync state. */
export function AsyncBoundary<T>({ state, children, minHeight = 120 }: AsyncBoundaryProps<T>) {
  if (state.loading && state.data === undefined) {
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
