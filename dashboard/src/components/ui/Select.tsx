import { useEffect, useRef, useState } from 'react'
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

/**
 * A styled dropdown. The native <select> renders its popup with the OS's own
 * chrome, which ignores the app's theme and can't be styled, so this draws the
 * menu itself and keeps the listbox keyboard behaviour that the native control
 * would otherwise have given us for free.
 */
export function Select({ value, options, onChange, label, className, valueStyle }: SelectProps) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const root = useRef<HTMLDivElement>(null)

  const selected = options.find((o) => o.value === value)

  // A click anywhere else dismisses the menu, matching what a native select does.
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false)
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
    <div ref={root} className={`${styles.root} ${className ?? ''}`} onKeyDown={onKeyDown}>
      <button
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

      {open ? (
        <ul className={styles.menu} role="listbox" aria-label={label}>
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
        </ul>
      ) : null}
    </div>
  )
}
