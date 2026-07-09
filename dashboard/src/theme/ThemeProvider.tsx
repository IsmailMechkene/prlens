import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { DEFAULT_THEME, themeToCssVars } from './theme'
import type { Theme } from './theme'

interface ThemeContextValue {
  theme: Theme
  setTheme: (patch: Partial<Theme>) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

const STORAGE_KEY = 'prlens.theme'

function loadTheme(): Theme {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return { ...DEFAULT_THEME, ...(JSON.parse(raw) as Partial<Theme>) }
  } catch {
    /* ignore malformed storage */
  }
  return DEFAULT_THEME
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(loadTheme)

  // Apply theme tokens to the document root and persist.
  useEffect(() => {
    const root = document.documentElement
    const vars = themeToCssVars(theme)
    for (const [key, value] of Object.entries(vars)) {
      root.style.setProperty(key, value)
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(theme))
    } catch {
      /* ignore quota / privacy-mode errors */
    }
  }, [theme])

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      setTheme: (patch) => setThemeState((prev) => ({ ...prev, ...patch })),
    }),
    [theme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider')
  return ctx
}
