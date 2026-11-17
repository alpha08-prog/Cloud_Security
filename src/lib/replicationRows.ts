// View-model rows for the replication charts, derived from results/published/replication.json.
import type { PairedRow } from '../components/charts/PairedBarChart'
import { AXIS_LABEL } from '../data/axes'
import { PERIOD_LABEL } from '../data/replication'
import type { Axis, Interval, ReplicationResult } from '../data/resultTypes'
import { CATEGORY_SHARES } from '../data/stats'
import { UNDER_SOLVED, getCategory } from '../data/taxonomy'

export interface IntervalValue {
  value: number | null
  ci: Interval | null
}

export interface IntervalRow {
  key: string
  label: string
  /** Tick label on narrow screens. */
  short?: string
  values: Record<string, IntervalValue>
}

const AXIS_SHORT: Record<Axis, string> = {
  'hypervisor-vulnerabilities': 'Hypervisor',
  'cross-vm-attacks': 'Cross-VM',
  isolation: 'Isolation',
  'data-leakage': 'Leakage',
  'vm-identification': 'VM ID',
}

/** Periods in display order: the survey, the three eras, then pooled. */
export function periods(doc: ReplicationResult): string[] {
  return ['2012', ...doc.protocol.eras.map((e) => e.id), 'pooled']
}

export const periodLabel = (p: string) => PERIOD_LABEL[p] ?? p

/** Figures 6 & 8 recomputed for one period, in the survey's category order. */
export function categoryRows(doc: ReplicationResult, period: string): PairedRow[] {
  return CATEGORY_SHARES.map((s) => {
    const row = doc.categories.find((r) => r.era === period && r.category === s.category)
    return {
      key: s.category,
      label: getCategory(s.category).label,
      concern: round1(row?.concernPct ?? 0),
      solution: round1(row?.solutionPct ?? 0),
      highlight: s.category === UNDER_SOLVED,
    }
  })
}

/** The virtualization gap per period (one series), for the interval chart. */
export function virtualizationGapRows(doc: ReplicationResult): IntervalRow[] {
  return periods(doc).map((p) => {
    const row = doc.categories.find((r) => r.era === p && r.category === UNDER_SOLVED)
    return {
      key: p,
      label: periodLabel(p),
      short: p === '2012' ? '2012' : p === 'pooled' ? 'Pooled' : periodLabel(p),
      values: { gap: { value: row?.gapPts ?? null, ci: row?.gapCi ?? null } },
    }
  })
}

/** Figure 11's method: solution/concern ratio per sub-issue, 2012 vs pooled 2013–26. */
export function axisRatioRows(doc: ReplicationResult): IntervalRow[] {
  const axes = [...new Set(doc.axes.map((a) => a.axis))] as Axis[]
  return axes.map((axis) => {
    const at = (era: string) => doc.axes.find((a) => a.era === era && a.axis === axis)
    return {
      key: axis,
      label: AXIS_LABEL[axis],
      short: AXIS_SHORT[axis],
      values: {
        survey: { value: at('2012')?.ratio ?? null, ci: null },
        pooled: { value: at('pooled')?.ratio ?? null, ci: at('pooled')?.ratioCi ?? null },
      },
    }
  })
}

export interface CveRow {
  year: number
  partial: boolean
  total: number
  [axis: string]: number | boolean | null
}

/** CVEs per 10,000 published, per year and axis. */
export function cveRows(doc: ReplicationResult): CveRow[] {
  return doc.cve.years.map((y) => ({ year: y.year, partial: y.partial, total: y.total, ...y.per10k }))
}

/** The robustness variants for one period, main first. */
export function robustnessRows(doc: ReplicationResult) {
  const ids = ['main', 'RB1', 'RB2', 'RB3', 'RB4'] as const
  return ids.map((id) => {
    const rows = doc.robustness.filter((r) => r.id === id)
    return {
      id,
      label: rows[0]?.label ?? id,
      byPeriod: Object.fromEntries(rows.map((r) => [r.era, { value: r.gapPts, ci: r.gapCi }])) as Record<
        string,
        IntervalValue
      >,
    }
  })
}

export function inScopeTotals(doc: ReplicationResult) {
  return doc.flow.reduce(
    (acc, f) => ({ analysed: acc.analysed + f.analysed, inScope: acc.inScope + f.inScope }),
    { analysed: 0, inScope: 0 },
  )
}

const round1 = (v: number) => Math.round(v * 10) / 10
