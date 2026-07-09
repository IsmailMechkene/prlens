import styles from './Toggle.module.css'

interface ToggleProps {
  checked: boolean
  onChange: (next: boolean) => void
  label?: string
}

/** Accessible on/off switch matching the design's pill toggle. */
export function Toggle({ checked, onChange, label }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      className={styles.toggle}
      onClick={() => onChange(!checked)}
    >
      <span
        className={styles.track}
        data-on={checked}
        style={{ background: checked ? 'var(--success-emphasis)' : 'var(--border-default)' }}
      >
        <span className={styles.knob} style={{ left: checked ? '19px' : '2px' }} />
      </span>
    </button>
  )
}
