import { useTheme } from '../../theme/ThemeProvider'
import { ACCENTS, CORNERS, DENSITIES } from '../../theme/theme'
import type { Corners, Density } from '../../theme/theme'
import { Icon } from '../ui/Icon'
import styles from './ThemeControls.module.css'

/** Short labels for the segmented controls: "Comfortable" and "Spacious" do not
 *  fit side by side in a 260px sidebar, and truncating them reads as broken. The
 *  full word stays as the accessible name. */
const CORNER_LABELS: Record<Corners, string> = {
  Sharp: 'Sharp',
  Rounded: 'Round',
  Pill: 'Pill',
}

const DENSITY_LABELS: Record<Density, string> = {
  Compact: 'Compact',
  Comfortable: 'Cosy',
  Spacious: 'Roomy',
}

/** Live theme editor (accent / corners / density) — an addition over the
 *  static design, surfaced from the sidebar settings gear. */
export function ThemeControls({ onClose }: { onClose?: () => void }) {
  const { theme, setTheme } = useTheme()

  return (
    <div className={styles.panel} role="dialog" aria-label="Appearance">
      <div className={styles.head}>
        <span className={styles.title}>Appearance</span>
        {onClose && (
          <button
            type="button"
            className={styles.close}
            aria-label="Close appearance settings"
            onClick={onClose}
          >
            <Icon name="x" size={14} />
          </button>
        )}
      </div>

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
              aria-label={c}
              aria-pressed={theme.corners === c}
              onClick={() => setTheme({ corners: c as Corners })}
            >
              {CORNER_LABELS[c]}
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
              aria-label={d}
              aria-pressed={theme.density === d}
              onClick={() => setTheme({ density: d as Density })}
            >
              {DENSITY_LABELS[d]}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
