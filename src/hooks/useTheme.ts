import { useCallback, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

// Must match the key used by the inline script in index.html.
const STORAGE_KEY = 'ctl-theme'
const DARK_QUERY = '(prefers-color-scheme: dark)'

function isTheme(value: unknown): value is Theme {
  return value === 'light' || value === 'dark'
}

function readStored(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return isTheme(value) ? value : null
  } catch {
    return null
  }
}

function writeStored(theme: Theme) {
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // Storage unavailable (private mode, blocked site data) — theme still applies.
  }
}

function initialTheme(): Theme {
  const fromDom = document.documentElement.dataset.theme
  if (isTheme(fromDom)) return fromDom
  return readStored() ?? (window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light')
}

/**
 * Light/dark theme. Follows the OS preference until the user picks one,
 * after which the choice is remembered.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(initialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    const query = window.matchMedia(DARK_QUERY)
    const onChange = (event: MediaQueryListEvent) => {
      if (!readStored()) setTheme(event.matches ? 'dark' : 'light')
    }
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  const toggle = useCallback(() => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    writeStored(next)
    setTheme(next)
  }, [theme])

  return { theme, toggle }
}
