import { useId } from 'react'

interface QualityTrendChartProps {
  /** Score samples, oldest → newest. */
  data: number[]
  min?: number
  max?: number
}

/** Responsive line + area sparkline for the quality-score trend. */
export function QualityTrendChart({ data, min = 60, max = 95 }: QualityTrendChartProps) {
  const gradientId = useId()
  const W = 660
  const H = 200
  const pad = 6

  if (data.length < 2) return null

  const x = (i: number) => pad + (i * (W - 2 * pad)) / (data.length - 1)
  const y = (v: number) => H - pad - ((v - min) / (max - min)) * (H - 2 * pad)

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
      aria-label="Quality score trend over the last 30 days"
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
      <path d={area} fill={`url(#${gradientId})`} />
      <path
        d={line}
        fill="none"
        stroke="var(--pa)"
        strokeWidth={2.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={last[0]} cy={last[1]} r={4} fill="var(--bg-inset)" stroke="var(--pa)" strokeWidth={2.5} />
    </svg>
  )
}
