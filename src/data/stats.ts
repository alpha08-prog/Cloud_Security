// Quantitative data, mirrored from docs/paper-content.md §5.
import type { CategoryId } from './taxonomy'

// ---------------------------------------------------------------------------
// Grouped categories — Figures 6 (concerns) & 8 (solutions). Exact; each column
// sums to 100.

export interface CategoryShare {
  category: CategoryId
  /** % of concern citations. */
  concern: number
  /** % of solution citations. */
  solution: number
  /**
   * Coverage gap in percentage points: solution − concern. Negative means the
   * category is raised more often than it is solved.
   *
   * paper-content.md states the formula as "concern − solution" but its Gap
   * column (Legal +3, Virtualization −9, …) and its "negative = under-solved"
   * rule both match solution − concern, so that is what we compute.
   */
  gap: number
}

const share = (category: CategoryId, concern: number, solution: number): CategoryShare => ({
  category,
  concern,
  solution,
  gap: solution - concern,
})

/** In the source table's order (concern % descending). */
export const CATEGORY_SHARES: readonly CategoryShare[] = [
  share('legal-issues', 24, 27),
  share('compliance', 22, 29),
  share('governance', 17, 14),
  share('virtualization', 12, 3),
  share('data-security', 10, 9),
  share('interfaces', 8, 10),
  share('network-security', 7, 8),
]

const shareByCategory = new Map(CATEGORY_SHARES.map((s) => [s.category, s]))
export const getShare = (category: CategoryId): CategoryShare => shareByCategory.get(category)!

// ---------------------------------------------------------------------------
// Sub-categories — Figures 5 (concerns) & 7 (solutions). Read from charts, so
// approximate; the columns sum to roughly (not exactly) 100.

export type SubcategoryName =
  | 'Legislation'
  | 'Service conformity'
  | 'Data control'
  | 'Isolation'
  | 'Audit'
  | 'Provider privilege'
  | 'Cryptography'
  | 'Security control'
  | 'Transfer security'
  | 'SLA'
  | 'Data location'
  | 'Hypervisor vulnerabilities'
  | 'e-Discovery'
  | 'Lock-in'
  | 'Authentication'
  | 'Redundancy'
  | 'Disposal'
  | 'User interface'
  | 'Administrative interface'
  | 'API'
  | 'Firewalling'
  | 'Security configuration'
  | 'Loss of service'

/** Figure 5, % of concern citations (approximate). */
export const SUBCATEGORY_CONCERNS: Readonly<Record<SubcategoryName, number>> = {
  Legislation: 10,
  'Service conformity': 9,
  'Data control': 9,
  Isolation: 7,
  Audit: 6,
  'Provider privilege': 6,
  Cryptography: 6,
  'Security control': 5,
  'Transfer security': 5,
  SLA: 5,
  'Data location': 5,
  'Hypervisor vulnerabilities': 5,
  'e-Discovery': 4,
  'Lock-in': 3,
  Authentication: 3,
  Redundancy: 2,
  Disposal: 2,
  'User interface': 2,
  'Administrative interface': 2,
  API: 2,
  Firewalling: 2,
  'Security configuration': 1,
  'Loss of service': 1,
}

/** Figure 7, % of solution citations (approximate). */
export const SUBCATEGORY_SOLUTIONS: Readonly<Record<SubcategoryName, number>> = {
  'Service conformity': 12,
  Legislation: 12,
  Audit: 8,
  'Data control': 8,
  SLA: 7,
  'Provider privilege': 7,
  'Transfer security': 5,
  'Data location': 4,
  Cryptography: 4,
  'e-Discovery': 4,
  'Security control': 3,
  Authentication: 3,
  'User interface': 3,
  'Lock-in': 3,
  Redundancy: 3,
  'Administrative interface': 2,
  Disposal: 2,
  Firewalling: 2,
  'Hypervisor vulnerabilities': 2,
  API: 2,
  'Loss of service': 1,
  Isolation: 1,
  'Security configuration': 1,
}

export interface SubcategoryShare {
  name: SubcategoryName
  concern: number
  solution: number
  /** solution − concern, as for categories. */
  gap: number
}

/** Figures 5 & 7 joined by name, in Figure 5's order (concern % descending). */
export const SUBCATEGORY_SHARES: readonly SubcategoryShare[] = (
  Object.keys(SUBCATEGORY_CONCERNS) as SubcategoryName[]
).map((name) => ({
  name,
  concern: SUBCATEGORY_CONCERNS[name],
  solution: SUBCATEGORY_SOLUTIONS[name],
  gap: SUBCATEGORY_SOLUTIONS[name] - SUBCATEGORY_CONCERNS[name],
}))

// ---------------------------------------------------------------------------
// Virtualization radar — Figure 11. Approximate values read from the chart,
// on its own scale of roughly 0–25.

export interface VirtualizationIssue {
  issue: string
  concern: number
  solution: number
}

export const VIRTUALIZATION_RADAR: readonly VirtualizationIssue[] = [
  { issue: 'Isolation', concern: 22, solution: 3 },
  { issue: 'Cross-VM attacks', concern: 20, solution: 1 },
  { issue: 'Hypervisor vulnerabilities', concern: 20, solution: 2 },
  { issue: 'Data leakage', concern: 18, solution: 1 },
  { issue: 'VM identification', concern: 15, solution: 1 },
]

export const VIRTUALIZATION_RADAR_MAX = 25
