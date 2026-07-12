import {
  ArrowRight,
  Book,
  BookMarked,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  CirclePlus,
  Clock,
  FileCode,
  Gauge,
  GitPullRequest,
  LayoutDashboard,
  Lock,
  MessageSquare,
  Plus,
  Save,
  ScanEye,
  Search,
  Server,
  Settings,
  ShieldAlert,
  SlidersHorizontal,
  Tags,
  Trash2,
  Users,
  Workflow,
  X,
  Zap,
} from 'lucide-react'
import type { LucideIcon, LucideProps } from 'lucide-react'

/**
 * Explicit registry of the icons used across the app. Keeping this map (rather
 * than importing all of lucide) means only these icons are bundled, while data
 * can still reference icons by their kebab-case name as in the source design.
 */
const REGISTRY: Record<string, LucideIcon> = {
  'arrow-right': ArrowRight,
  book: Book,
  'book-marked': BookMarked,
  check: Check,
  'circle-check-big': CheckCircle2,
  'chevron-right': ChevronRight,
  'circle-alert': CircleAlert,
  'circle-plus': CirclePlus,
  clock: Clock,
  'file-code': FileCode,
  gauge: Gauge,
  'git-pull-request': GitPullRequest,
  'layout-dashboard': LayoutDashboard,
  lock: Lock,
  'message-square': MessageSquare,
  plus: Plus,
  save: Save,
  'scan-eye': ScanEye,
  search: Search,
  server: Server,
  settings: Settings,
  'shield-alert': ShieldAlert,
  'sliders-horizontal': SlidersHorizontal,
  tags: Tags,
  'trash-2': Trash2,
  users: Users,
  workflow: Workflow,
  x: X,
  zap: Zap,
}

export interface IconProps extends Omit<LucideProps, 'ref'> {
  /** kebab-case icon name, e.g. "git-pull-request". */
  name: string
}

export function Icon({ name, size = '1em', strokeWidth = 2, ...rest }: IconProps) {
  const LucideIconComp = REGISTRY[name]
  if (!LucideIconComp) {
    if (import.meta.env.DEV) console.warn(`Icon: unknown name "${name}"`)
    return null
  }
  return <LucideIconComp size={size} strokeWidth={strokeWidth} {...rest} />
}
