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

  // Visual gap between slices. It is subtracted from each arc, so it can never be
  // taken out of an arc that is shorter than it is: a negative value in a
  // stroke-dasharray invalidates the whole property, and the browser then strokes a
  // solid full ring in that segment's colour, right over the real arcs. A category
  // with zero issues used to do exactly that — painting the entire donut one colour
  // and hiding the actual breakdown.
  const GAP = 3

  // Arc lengths and their cumulative start offsets, computed immutably so
  // there is no render-time reassignment. Empty categories take no arc at all —
  // they still appear in the legend, with a count of zero.
  const lengths = segments.map((s) => (total > 0 ? (s.value / total) * C : 0))
  const offsets = lengths.map((_, i) =>
    lengths.slice(0, i).reduce((sum, len) => sum + len, 0),
  )
  const arcs = segments
    .map((segment, i) => {
      const length = lengths[i]
      const gap = Math.min(GAP, length * 0.4) // a thin slice gives up a thin gap
      return { segment, dash: length - gap, offset: offsets[i] }
    })
    .filter((arc) => arc.dash > 0)

  return (
    <svg
      viewBox="0 0 150 150"
      style={{ width: 132, height: 132 }}
      role="img"
      aria-label={`${total} issues caught across ${segments.length} categories`}
    >
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="var(--border-muted)" strokeWidth={sw} />
      {arcs.map(({ segment, dash, offset }) => (
        <circle
          key={segment.category}
          cx={cx}
          cy={cy}
          r={R}
          fill="none"
          stroke={issueColor(segment.category)}
          strokeWidth={sw}
          strokeDasharray={`${dash} ${C - dash}`}
          strokeDashoffset={-offset}
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
