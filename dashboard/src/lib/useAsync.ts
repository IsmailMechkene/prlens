import { useCallback, useEffect, useState } from 'react'

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

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    let alive = true
    // Mark this request as in-flight when deps change (preserve any previously
    // loaded data so panels don't flash empty on refetch). This deliberate
    // begin-fetch reset is the one synchronous setState a fetch hook needs.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState((prev) => ({ data: prev.data, loading: true, error: undefined }))
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
