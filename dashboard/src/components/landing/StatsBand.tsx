import styles from './StatsBand.module.css'

// Marketing copy — static, not backend-driven.
const STATS = [
  { value: '12,000+', label: 'repositories connected' },
  { value: '450K', label: 'pull requests reviewed' },
  { value: '4.2s', label: 'median time to first comment' },
  { value: '31%', label: 'fewer bugs reaching main' },
]

/** Horizontal proof band between the hero preview and the feature sections. */
export function StatsBand() {
  return (
    <section className={styles.band}>
      {STATS.map((s) => (
        <div key={s.label} className={styles.stat}>
          <div className={styles.value}>{s.value}</div>
          <div className={styles.label}>{s.label}</div>
        </div>
      ))}
    </section>
  )
}
