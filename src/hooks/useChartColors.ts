import { useEffect, useState } from 'react'

// Recharts draws SVG presentation attributes, so chart colors are resolved from
// the theme's CSS variables in JS and re-read whenever the theme flips.
const TOKENS = {
  concern: '--series-concern',
  solution: '--series-solution',
  highlight: '--highlight',
  highlightSoft: '--highlight-soft',
  muted: '--chart-muted',
  grid: '--chart-grid',
  axis: '--chart-axis',
  text: '--text',
  textMuted: '--text-muted',
  surface: '--surface',
  surface2: '--surface-2',
  accent: '--accent',
} as const

export type ChartColors = { [K in keyof typeof TOKENS]: string }

function readColors(): ChartColors {
  const style = getComputedStyle(document.documentElement)
  return Object.fromEntries(
    Object.entries(TOKENS).map(([key, cssVar]) => [key, style.getPropertyValue(cssVar).trim()]),
  ) as ChartColors
}

export function useChartColors(): ChartColors {
  const [colors, setColors] = useState(readColors)

  useEffect(() => {
    const observer = new MutationObserver(() => setColors(readColors()))
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => observer.disconnect()
  }, [])

  return colors
}
