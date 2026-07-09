import type { IssueCategory, ReviewStatus } from './types'

/** Colour treatment for a quality score badge. */
export interface ScoreStyle {
  color: string
  bg: string
  border: string
}

/** Score → colour band (green ≥80, amber ≥50, red below). */
export function scoreStyle(score: number): ScoreStyle {
  if (score > 80) {
    return {
      color: 'var(--success)',
      bg: 'rgba(63,185,80,0.12)',
      border: 'rgba(63,185,80,0.35)',
    }
  }
  if (score >= 50) {
    return {
      color: 'var(--attention)',
      bg: 'rgba(210,153,34,0.12)',
      border: 'rgba(210,153,34,0.35)',
    }
  }
  return {
    color: 'var(--danger)',
    bg: 'rgba(248,81,73,0.12)',
    border: 'rgba(248,81,73,0.35)',
  }
}

export interface StatusMeta {
  label: string
  color: string
  /** lucide icon name. */
  icon: string
}

export function statusMeta(status: ReviewStatus): StatusMeta {
  switch (status) {
    case 'approved':
      return { label: 'Approved', color: 'var(--success)', icon: 'circle-check-big' }
    case 'changes':
      return { label: 'Changes requested', color: 'var(--attention)', icon: 'circle-alert' }
    default:
      return { label: 'Incomplete', color: 'var(--fg-muted)', icon: 'clock' }
  }
}

/** Fixed colours for issue-breakdown categories (Quality tracks the accent). */
export function issueColor(category: IssueCategory): string {
  switch (category) {
    case 'Security':
      return 'var(--danger)'
    case 'Quality':
      return 'var(--pa)'
    case 'Performance':
      return 'var(--attention)'
    case 'Style':
      return '#8b949e'
  }
}
