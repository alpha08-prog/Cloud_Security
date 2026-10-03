// View-model rows for the concern/solution charts, derived from src/data.
import type { GapRow } from '../components/charts/GapChart'
import { CATEGORY_SHARES, SUBCATEGORY_SHARES, VIRTUALIZATION_RADAR } from '../data/stats'
import { UNDER_SOLVED, categoryOfSubcategory, getCategory } from '../data/taxonomy'

/** The seven categories (Figs 6 & 8), sorted by concern share, descending. */
export const CATEGORY_ROWS: readonly GapRow[] = [...CATEGORY_SHARES]
  .sort((a, b) => b.concern - a.concern || b.solution - a.solution)
  .map((s) => ({
    key: s.category,
    label: getCategory(s.category).label,
    concern: s.concern,
    solution: s.solution,
    gap: s.gap,
    highlight: s.category === UNDER_SOLVED,
  }))

/** Same rows, most under-solved first. */
export const CATEGORY_ROWS_BY_GAP: readonly GapRow[] = [...CATEGORY_ROWS].sort(
  (a, b) => a.gap - b.gap,
)

/** Sub-categories (Figs 5 & 7, approximate), sorted by concern share. */
export const SUBCATEGORY_ROWS: readonly GapRow[] = [...SUBCATEGORY_SHARES]
  .sort((a, b) => b.concern - a.concern || b.solution - a.solution)
  .map((s) => ({
    key: s.name,
    label: s.name,
    concern: s.concern,
    solution: s.solution,
    gap: s.gap,
    highlight: categoryOfSubcategory(s.name) === UNDER_SOLVED,
  }))

/** Virtualization sub-issues (Fig 11, approximate). */
export const VIRTUALIZATION_ROWS: readonly GapRow[] = VIRTUALIZATION_RADAR.map((v) => ({
  key: v.issue,
  label: v.issue,
  concern: v.concern,
  solution: v.solution,
  gap: v.solution - v.concern,
}))

export const largestDeficit = (rows: readonly GapRow[]): GapRow =>
  rows.reduce((worst, row) => (row.gap < worst.gap ? row : worst))
