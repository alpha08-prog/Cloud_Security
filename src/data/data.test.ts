// Integrity checks for the content layer: the figures must match
// docs/paper-content.md, and the modules must agree with each other.
import { describe, expect, it } from 'vitest'
import { VIRTUALIZATION_DEFENSE_NOTES } from '../sections/side-channel/defenseNotes'
import { DEFENSES } from './defenses'
import { FRAMEWORKS } from './frameworks'
import {
  CATEGORY_SHARES,
  SUBCATEGORY_CONCERNS,
  SUBCATEGORY_SHARES,
  SUBCATEGORY_SOLUTIONS,
  VIRTUALIZATION_RADAR,
  VIRTUALIZATION_RADAR_MAX,
} from './stats'
import {
  CATEGORIES,
  DIMENSIONS,
  TAXONOMY_FIGURES,
  UNDER_SOLVED,
  categoryOfSubcategory,
  getCategory,
  indexFigure,
  type CategoryId,
  type TreeNode,
} from './taxonomy'

const sum = (values: readonly number[]) => values.reduce((total, v) => total + v, 0)
const ALL_CATEGORIES = CATEGORIES.map((c) => c.id)

describe('grouped categories (Figures 6 & 8)', () => {
  it('matches the table in paper-content.md §5', () => {
    const table: Record<CategoryId, [concern: number, solution: number]> = {
      'legal-issues': [24, 27],
      compliance: [22, 29],
      governance: [17, 14],
      virtualization: [12, 3],
      'data-security': [10, 9],
      interfaces: [8, 10],
      'network-security': [7, 8],
    }
    expect(CATEGORY_SHARES).toHaveLength(7)
    for (const s of CATEGORY_SHARES) {
      expect([s.concern, s.solution], s.category).toEqual(table[s.category])
    }
  })

  it('covers every category exactly once', () => {
    expect(CATEGORY_SHARES.map((s) => s.category).sort()).toEqual([...ALL_CATEGORIES].sort())
  })

  it('sums each series to exactly 100', () => {
    expect(sum(CATEGORY_SHARES.map((s) => s.concern))).toBe(100)
    expect(sum(CATEGORY_SHARES.map((s) => s.solution))).toBe(100)
  })

  it('computes gap as solution − concern', () => {
    for (const s of CATEGORY_SHARES) expect(s.gap, s.category).toBe(s.solution - s.concern)
  })

  it('has virtualization as the largest deficit (−9)', () => {
    const worst = [...CATEGORY_SHARES].sort((a, b) => a.gap - b.gap)[0]
    expect(worst.category).toBe(UNDER_SOLVED)
    expect(worst.gap).toBe(-9)
  })
})

describe('sub-categories (Figures 5 & 7, approximate)', () => {
  it('lists the same sub-categories for concerns and solutions', () => {
    expect(Object.keys(SUBCATEGORY_SOLUTIONS).sort()).toEqual(
      Object.keys(SUBCATEGORY_CONCERNS).sort(),
    )
  })

  it('sums each series to roughly 100 (values were read from charts)', () => {
    for (const total of [
      sum(SUBCATEGORY_SHARES.map((s) => s.concern)),
      sum(SUBCATEGORY_SHARES.map((s) => s.solution)),
    ]) {
      expect(total).toBeGreaterThanOrEqual(95)
      expect(total).toBeLessThanOrEqual(105)
    }
  })

  it('places every sub-category in a taxonomy tree, except the two with no tree node', () => {
    const unplaced = SUBCATEGORY_SHARES.filter((s) => !categoryOfSubcategory(s.name)).map(
      (s) => s.name,
    )
    expect(unplaced.sort()).toEqual(['Legislation', 'Service conformity'])
  })
})

describe('virtualization radar (Figure 11, approximate)', () => {
  it('stays within the chart scale', () => {
    for (const v of VIRTUALIZATION_RADAR) {
      for (const value of [v.concern, v.solution]) {
        expect(value).toBeGreaterThanOrEqual(0)
        expect(value).toBeLessThanOrEqual(VIRTUALIZATION_RADAR_MAX)
      }
    }
  })

  it('uses the virtualization sub-categories from Figure 2', () => {
    for (const v of VIRTUALIZATION_RADAR) {
      expect(categoryOfSubcategory(v.issue), v.issue).toBe('virtualization')
    }
  })

  it('shows concern exceeding solution for every sub-issue', () => {
    for (const v of VIRTUALIZATION_RADAR) expect(v.concern, v.issue).toBeGreaterThan(v.solution)
  })
})

describe('taxonomy (Figures 1–4)', () => {
  it('assigns each category to exactly one dimension, consistently', () => {
    const fromDimensions = DIMENSIONS.flatMap((d) =>
      d.categories.map((id) => [id, d.id] as const),
    )
    expect(fromDimensions.map(([id]) => id).sort()).toEqual([...ALL_CATEGORIES].sort())
    for (const [id, dimension] of fromDimensions) {
      expect(getCategory(id).dimension, id).toBe(dimension)
    }
  })

  it('gives every node a unique id within its figure', () => {
    for (const figure of TAXONOMY_FIGURES) {
      const ids: string[] = []
      const visit = (node: TreeNode) => {
        ids.push(node.id)
        node.children?.forEach(visit)
      }
      visit(figure.root)
      expect(new Set(ids).size, `Figure ${figure.figure}`).toBe(ids.length)
      expect(indexFigure(figure).size).toBe(ids.length)
    }
  })

  it('places all seven categories across Figures 2–4, once each', () => {
    const placed = TAXONOMY_FIGURES.slice(1).flatMap(
      (figure) => figure.root.children?.map((c) => c.category) ?? [],
    )
    expect(placed.sort()).toEqual([...ALL_CATEGORIES].sort())
  })

  it('resolves every node in Figures 2–4 to a dimension', () => {
    for (const figure of TAXONOMY_FIGURES.slice(1)) {
      for (const [id, context] of indexFigure(figure)) {
        expect(context.dimension, id).toBeDefined()
      }
    }
  })

  it('marks the two cross-VM attack examples as emphasised', () => {
    const architecture = indexFigure(TAXONOMY_FIGURES[1])
    const emphasised = [...architecture.values()]
      .filter((c) => c.node.emphasis)
      .map((c) => c.node.label)
    expect(emphasised).toEqual([
      'Cryptographic key stealing',
      'VM placement / overlapping attacks',
    ])
  })
})

describe('defense matrix', () => {
  it('answers every category exactly once, with at least one control', () => {
    expect(DEFENSES.map((d) => d.category).sort()).toEqual([...ALL_CATEGORIES].sort())
    for (const d of DEFENSES) expect(d.controls.length, d.category).toBeGreaterThan(0)
  })

  it('has a side-channel note for each virtualization control, and no stray notes', () => {
    const controls = DEFENSES.find((d) => d.category === 'virtualization')!.controls
    expect(Object.keys(VIRTUALIZATION_DEFENSE_NOTES).sort()).toEqual([...controls].sort())
  })
})

describe('frameworks (Tables 1 & 2)', () => {
  it('has unique ids and covers CSA, ENISA and NIST', () => {
    expect(new Set(FRAMEWORKS.map((f) => f.id)).size).toBe(FRAMEWORKS.length)
    expect(new Set(FRAMEWORKS.map((f) => f.org))).toEqual(new Set(['CSA', 'ENISA', 'NIST']))
  })

  it('lists the seven CSA top threats', () => {
    const topThreats = FRAMEWORKS.find((f) => f.id === 'csa-top-threats')!
    expect(topThreats.lists?.[0].items).toHaveLength(7)
  })
})
