import { describe, expect, it } from 'vitest'
import {
  CATEGORY_ROWS,
  CATEGORY_ROWS_BY_GAP,
  SUBCATEGORY_ROWS,
  VIRTUALIZATION_ROWS,
  largestDeficit,
} from './chartRows'
import { cx, formatGap, formatPercent } from './format'

describe('formatGap', () => {
  it('signs the value with a true minus sign', () => {
    expect(formatGap(3)).toBe('+3 pts')
    expect(formatGap(-9)).toBe('−9 pts')
    expect(formatGap(0)).toBe('0 pts')
    expect(formatGap(-2, '')).toBe('−2')
  })
})

describe('formatPercent', () => {
  it('appends a percent sign', () => {
    expect(formatPercent(12)).toBe('12%')
  })
})

describe('cx', () => {
  it('joins only truthy class names', () => {
    expect(cx('a', false, null, undefined, 'b')).toBe('a b')
  })
})

describe('chart rows', () => {
  it('sorts categories by concern share, descending', () => {
    const concerns = CATEGORY_ROWS.map((r) => r.concern)
    expect(concerns).toEqual([...concerns].sort((a, b) => b - a))
  })

  it('highlights only virtualization among the categories', () => {
    expect(CATEGORY_ROWS.filter((r) => r.highlight).map((r) => r.key)).toEqual(['virtualization'])
  })

  it('puts virtualization first when sorted by gap', () => {
    expect(CATEGORY_ROWS_BY_GAP[0].key).toBe('virtualization')
    expect(largestDeficit(CATEGORY_ROWS).key).toBe('virtualization')
  })

  it('highlights the virtualization sub-categories (Isolation, Hypervisor vulnerabilities)', () => {
    expect(
      SUBCATEGORY_ROWS.filter((r) => r.highlight)
        .map((r) => r.key)
        .sort(),
    ).toEqual(['Hypervisor vulnerabilities', 'Isolation'])
  })

  it('derives virtualization gaps as solution − concern', () => {
    for (const r of VIRTUALIZATION_ROWS) expect(r.gap).toBe(r.solution - r.concern)
  })
})
