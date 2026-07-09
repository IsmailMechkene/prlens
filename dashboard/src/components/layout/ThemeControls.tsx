import { useTheme } from '../../theme/ThemeProvider'
import { ACCENTS, CORNERS, DENSITIES } from '../../theme/theme'
import type { Corners, Density } from '../../theme/theme'
import styles from './ThemeControls.module.css'

/** Live theme editor (accent / corners / density) — an addition over the
 *  static design, surfaced from the sidebar settings gear. */
export function ThemeControls() {
  const { theme, setTheme } = useTheme()
  return (
    <div className={styles.panel}>
      <div className={styles.group}>
        <span className={styles.label}>Accent</span>
        <div className={styles.swatches}>
          {ACCENTS.map((c) => (
            <button
              key={c}
              type="button"
              aria-label={`Accent ${c}`}
              aria-pressed={theme.accent === c}
              className={styles.swatch}
              data-active={theme.accent === c}
              style={{ background: c }}
              onClick={() => setTheme({ accent: c })}
            />
          ))}
        </div>
      </div>

      <div className={styles.group}>
        <span className={styles.label}>Corners</span>
        <div className={styles.segmented}>
          {CORNERS.map((c) => (
            <button
              key={c}
              type="button"
              className={styles.segment}
              data-active={theme.corners === c}
              onClick={() => setTheme({ corners: c as Corners })}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.group}>
        <span className={styles.label}>Density</span>
        <div className={styles.segmented}>
          {DENSITIES.map((d) => (
            <button
              key={d}
              type="button"
              className={styles.segment}
              data-active={theme.density === d}
              onClick={() => setTheme({ density: d as Density })}
            >
              {d}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
