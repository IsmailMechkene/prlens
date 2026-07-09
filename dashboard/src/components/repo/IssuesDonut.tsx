import { issueColor } from '../../lib/reviewStyles'
import type { IssueBreakdown } from '../../lib/types'

/** Donut chart of issues by category with a total in the centre. */
export function IssuesDonut({ segments }: { segments: IssueBreakdown[] }) {
  const total = segments.reduce((sum, s) => sum + s.value, 0)
  const R = 58
  const C = 2 * Math.PI * R
  const cx = 75
  const cy = 75
  const sw = 20

  // Arc lengths and their cumulative start offsets, computed immutably so
  // there is no render-time reassignment.
  const lengths = segments.map((s) => (total > 0 ? (s.value / total) * C : 0))
  const offsets = lengths.map((_, i) =>
    lengths.slice(0, i).reduce((sum, len) => sum + len, 0),
  )

  return (
    <svg
      viewBox="0 0 150 150"
      style={{ width: 132, height: 132 }}
      role="img"
      aria-label={`${total} issues caught across ${segments.length} categories`}
    >
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="var(--border-muted)" strokeWidth={sw} />
      {segments.map((s, i) => (
        <circle
          key={s.category}
          cx={cx}
          cy={cy}
          r={R}
          fill="none"
          stroke={issueColor(s.category)}
          strokeWidth={sw}
          strokeDasharray={`${lengths[i] - 3} ${C - lengths[i] + 3}`}
          strokeDashoffset={-offsets[i]}
          transform={`rotate(-90 ${cx} ${cy})`}
          strokeLinecap="round"
        />
      ))}
      <text x={cx} y={cy - 4} textAnchor="middle" fill="var(--fg-default)" fontSize={26} fontWeight={700} fontFamily="Inter">
        {total}
      </text>
      <text x={cx} y={cy + 15} textAnchor="middle" fill="var(--fg-muted)" fontSize={10.5} fontFamily="Inter">
        issues
      </text>
    </svg>
  )
}
