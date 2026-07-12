import { useCallback, useEffect, useRef, useState } from 'react'

export interface AsyncState<T> {
  data: T | undefined
  loading: boolean
  error: Error | undefined
  /** Re-run the async function. */
  reload: () => void
}

interface InternalState<T> {
  data: T | undefined
  loading: boolean
  error: Error | undefined
}

/**
 * Minimal data-fetching hook. Runs `fn` on mount and whenever `deps` change,
 * tracking loading/error state and guarding against setState after unmount.
 *
 * `fn` must be stable or memoised by the caller; `deps` controls re-fetching.
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<InternalState<T>>({
    data: undefined,
    loading: true,
    error: undefined,
  })
  const [nonce, setNonce] = useState(0)
  const previousDeps = useRef(deps)

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    let alive = true

    // Whether this run is fetching something *different* (the deps changed), or the
    // same thing again (reload()). Data is kept across a reload, so a panel being
    // refreshed doesn't flash empty — but it must be dropped when the subject
    // changes, or the UI would go on showing the previous repo's reviews and
    // settings until the new ones arrive.
    const previous = previousDeps.current
    const subjectChanged =
      previous.length !== deps.length || deps.some((dep, i) => !Object.is(dep, previous[i]))
    previousDeps.current = deps

    // This deliberate begin-fetch reset is the one synchronous setState a fetch
    // hook needs.
    setState((prev) => ({
      data: subjectChanged ? undefined : prev.data,
      loading: true,
      error: undefined,
    }))
    fn()
      .then((result) => {
        if (alive) setState({ data: result, loading: false, error: undefined })
      })
      .catch((err: unknown) => {
        if (alive) {
          setState((prev) => ({
            data: prev.data,
            loading: false,
            error: err instanceof Error ? err : new Error(String(err)),
          }))
        }
      })
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  return { ...state, reload }
}
