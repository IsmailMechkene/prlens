import { useId } from 'react'

interface QualityTrendChartProps {
  /** Score samples, oldest → newest. */
  data: number[]
  /** Y-axis bounds. Derived from the data when not given. */
  min?: number
  max?: number
}

/**
 * The y-axis window for a set of scores.
 *
 * It used to be hardcoded to 60–95, which silently broke the chart on real data: a
 * score of 100 — what a clean PR gets — plots *above* the top of the canvas, and
 * anything under 60 below the bottom. The window now follows the data, with a
 * little headroom, and never leaves 0–100.
 */
function bounds(data: number[]): { min: number; max: number } {
  const lowest = Math.min(...data)
  const highest = Math.max(...data)

  // A flat series (identical scores, or a single review) has no range to scale
  // against, so give it one and let the line sit in the middle.
  const padding = Math.max((highest - lowest) * 0.15, 5)

  return {
    min: Math.max(0, Math.floor(lowest - padding)),
    max: Math.min(100, Math.ceil(highest + padding)),
  }
}

/** Responsive line + area sparkline for the quality-score trend. */
export function QualityTrendChart({ data, min, max }: QualityTrendChartProps) {
  const gradientId = useId()
  const W = 660
  const H = 200
  const pad = 6

  if (data.length === 0) {
    return (
      <div
        style={{
          height: 160,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 13,
          color: 'var(--fg-subtle)',
        }}
      >
        No reviews in the last 30 days yet.
      </div>
    )
  }

  const auto = bounds(data)
  const lo = min ?? auto.min
  const hi = max ?? auto.max
  const span = hi - lo || 1 // never divide by zero

  // One sample has no line to draw between two points, so it is plotted as a single
  // centred marker rather than rendering nothing at all — which is what a repo with
  // one day of reviews used to get.
  const single = data.length === 1

  const x = (i: number) => (single ? W / 2 : pad + (i * (W - 2 * pad)) / (data.length - 1))
  const y = (v: number) => H - pad - ((v - lo) / span) * (H - 2 * pad)

  const points = data.map((v, i) => [x(i), y(v)] as const)
  const line = points
    .map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`)
    .join(' ')
  const area = `${line} L${x(data.length - 1).toFixed(1)} ${H} L${x(0).toFixed(1)} ${H} Z`
  const last = points[points.length - 1]

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      style={{ width: '100%', height: '160px', display: 'block' }}
      role="img"
      aria-label={`Quality score trend over the last 30 days: ${data.join(', ')}`}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--pa)" stopOpacity={0.28} />
          <stop offset="100%" stopColor="var(--pa)" stopOpacity={0} />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((f) => (
        <line key={f} x1={0} x2={W} y1={H * f} y2={H * f} stroke="var(--border-muted)" strokeWidth={1} />
      ))}
      {!single && (
        <>
          <path d={area} fill={`url(#${gradientId})`} />
          <path
            d={line}
            fill="none"
            stroke="var(--pa)"
            strokeWidth={2.5}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </>
      )}
      <circle cx={last[0]} cy={last[1]} r={4} fill="var(--bg-inset)" stroke="var(--pa)" strokeWidth={2.5} />
    </svg>
  )
}
