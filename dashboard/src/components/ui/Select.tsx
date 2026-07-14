import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { CSSProperties, KeyboardEvent } from 'react'
import { Icon } from './Icon'
import styles from './Select.module.css'

export interface SelectOption {
  value: string
  label: string
}

interface SelectProps {
  value: string
  options: SelectOption[]
  onChange: (value: string) => void
  /** Accessible name — the control has no visible <label> of its own. */
  label: string
  /** Sizing for the wrapper, e.g. a flex rule from the parent's module. */
  className?: string
  /** Colour etc. for the selected value text. */
  valueStyle?: CSSProperties
}

/** Gap between the trigger and the menu, and the menu's min gap to the viewport edge. */
const GAP = 5
const MARGIN = 8
const MAX_HEIGHT = 220

interface MenuPos {
  top: number
  left: number
  width: number
  maxHeight: number
}

/**
 * A styled dropdown. The native <select> renders its popup with the OS's own
 * chrome, which ignores the app's theme and can't be styled, so this draws the
 * menu itself and keeps the listbox keyboard behaviour that the native control
 * would otherwise have given us for free.
 *
 * The menu is portalled to <body> and positioned as fixed: cards clip their
 * content with overflow:hidden to round their corners, which would otherwise cut
 * the menu off at the card's bottom edge and make the last options unreachable.
 */
export function Select({ value, options, onChange, label, className, valueStyle }: SelectProps) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [pos, setPos] = useState<MenuPos | null>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLUListElement>(null)

  const selected = options.find((o) => o.value === value)

  const place = useCallback(() => {
    const el = trigger.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const below = window.innerHeight - r.bottom - GAP - MARGIN
    const above = r.top - GAP - MARGIN
    // Drop upwards when the space under the trigger is too cramped to be usable.
    const up = below < Math.min(MAX_HEIGHT, 120) && above > below
    const maxHeight = Math.max(80, Math.min(MAX_HEIGHT, up ? above : below))
    setPos({
      top: up ? r.top - GAP - maxHeight : r.bottom + GAP,
      left: r.left,
      width: r.width,
      maxHeight,
    })
  }, [])

  // Fixed coordinates go stale as soon as anything scrolls, so recompute them.
  // Capture catches scrolling in the app's inner scroll container too, not just
  // on the window.
  useLayoutEffect(() => {
    if (!open) return
    place()
    window.addEventListener('scroll', place, true)
    window.addEventListener('resize', place)
    return () => {
      window.removeEventListener('scroll', place, true)
      window.removeEventListener('resize', place)
    }
  }, [open, place])

  // A click anywhere else dismisses the menu, matching what a native select does.
  // The menu is outside the trigger's subtree now, so it needs its own check.
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node
      if (!trigger.current?.contains(t) && !menu.current?.contains(t)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [open])

  const show = () => {
    const i = options.findIndex((o) => o.value === value)
    setActive(i < 0 ? 0 : i)
    setOpen(true)
  }

  const choose = (v: string) => {
    onChange(v)
    setOpen(false)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      setOpen(false)
      return
    }
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        show()
      }
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((i) => Math.min(i + 1, options.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      if (options[active]) choose(options[active].value)
    } else if (e.key === 'Tab') {
      setOpen(false)
    }
  }

  return (
    <div className={`${styles.root} ${className ?? ''}`} onKeyDown={onKeyDown}>
      <button
        ref={trigger}
        type="button"
        className={styles.trigger}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={label}
        onClick={() => (open ? setOpen(false) : show())}
      >
        <span className={styles.value} style={valueStyle}>
          {selected?.label ?? value}
        </span>
        <Icon name="chevron-down" size={14} className={styles.chevron} data-open={open} />
      </button>

      {open && pos
        ? createPortal(
            <ul
              ref={menu}
              className={styles.menu}
              role="listbox"
              aria-label={label}
              style={{
                top: pos.top,
                left: pos.left,
                width: pos.width,
                maxHeight: pos.maxHeight,
              }}
            >
              {options.map((o, i) => (
                <li
                  key={o.value}
                  role="option"
                  aria-selected={o.value === value}
                  className={styles.option}
                  data-active={i === active}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => choose(o.value)}
                >
                  <span className={styles.optionLabel}>{o.label}</span>
                  {o.value === value ? <Icon name="check" size={13} /> : null}
                </li>
              ))}
            </ul>,
            document.body,
          )
        : null}
    </div>
  )
}
