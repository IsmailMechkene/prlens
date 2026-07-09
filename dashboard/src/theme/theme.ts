/**
 * Theme model for PRLens.
 *
 * Mirrors the three theming props exposed by the original design:
 *   - accent  : brand colour (drives every --pa* token)
 *   - corners : border-radius scale
 *   - density : spacing multiplier (--dsc)
 */

export const ACCENTS = ['#58a6ff', '#a371f7', '#3fb950', '#e3b341', '#f778ba'] as const
export type Accent = (typeof ACCENTS)[number]

export const CORNERS = ['Sharp', 'Rounded', 'Pill'] as const
export type Corners = (typeof CORNERS)[number]

export const DENSITIES = ['Compact', 'Comfortable', 'Spacious'] as const
export type Density = (typeof DENSITIES)[number]

export interface Theme {
  accent: string
  corners: Corners
  density: Density
}

export const DEFAULT_THEME: Theme = {
  accent: '#58a6ff',
  corners: 'Rounded',
  density: 'Comfortable',
}

/** Radius pair for a given corner style. */
function radiusFor(corners: Corners): { rad: string; radSm: string } {
  switch (corners) {
    case 'Sharp':
      return { rad: '4px', radSm: '3px' }
    case 'Pill':
      return { rad: '22px', radSm: '13px' }
    default:
      return { rad: '12px', radSm: '8px' }
  }
}

/** Spacing multiplier for a given density. */
function densityScale(density: Density): number {
  switch (density) {
    case 'Compact':
      return 0.66
    case 'Spacious':
      return 1.34
    default:
      return 1
  }
}

/**
 * Resolve a theme into the CSS custom properties consumed across the app.
 * Applied to the root element by ThemeProvider.
 */
export function themeToCssVars(theme: Theme): Record<string, string> {
  const { accent } = theme
  const { rad, radSm } = radiusFor(theme.corners)
  return {
    '--pa': accent,
    '--pa-deep': `color-mix(in srgb, ${accent} 70%, #0a0f1e)`,
    '--pa-lite': `color-mix(in srgb, ${accent} 55%, #ffffff)`,
    '--pa-t12': `color-mix(in srgb, ${accent} 13%, transparent)`,
    '--pa-t40': `color-mix(in srgb, ${accent} 42%, transparent)`,
    '--rad': rad,
    '--rad-sm': radSm,
    '--dsc': String(densityScale(theme.density)),
  }
}

/** Translucent tint of the current accent, e.g. mix(15) → 15% accent. */
export function accentMix(pct: number): string {
  return `color-mix(in srgb, var(--pa) ${pct}%, transparent)`
}
