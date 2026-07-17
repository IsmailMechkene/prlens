import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import styles from './Modal.module.css'

interface ModalProps {
  open: boolean
  /** Escape, a backdrop click, or the close button. Suppress while a request is in flight. */
  onClose: () => void
  title: string
  /** "wide" fits media; the default width suits the confirm prompts. */
  size?: 'default' | 'wide'
  children: ReactNode
}

/**
 * Centred dialog rendered into <body>.
 *
 * A portal rather than an in-place element: the sidebar and the page header both
 * create their own stacking contexts, so a modal rendered where it is used would
 * be trapped underneath them.
 */
export function Modal({ open, onClose, title, size = 'default', children }: ModalProps) {
  const panel = useRef<HTMLDivElement>(null)
  const restoreFocusTo = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return

    restoreFocusTo.current = document.activeElement as HTMLElement | null
    panel.current?.focus()

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)

    // The page behind must not scroll under the dialog.
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = previousOverflow
      restoreFocusTo.current?.focus()
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div
      className={styles.backdrop}
      onClick={(e) => {
        // Only a click on the backdrop itself — not one that bubbled out of the panel.
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={panel}
        className={size === 'wide' ? `${styles.panel} ${styles.wide}` : styles.panel}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
      >
        {children}
      </div>
    </div>,
    document.body,
  )
}
