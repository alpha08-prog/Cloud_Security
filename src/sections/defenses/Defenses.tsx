import { useState } from 'react'
import { SegmentedControl } from '../../components/SegmentedControl'
import { DEFENSES } from '../../data/defenses'
import { getShare } from '../../data/stats'
import {
  CATEGORIES,
  DIMENSIONS,
  UNDER_SOLVED,
  getCategory,
  getDimension,
  type CategoryId,
  type DimensionId,
} from '../../data/taxonomy'
import { cx, formatGap } from '../../lib/format'
import './Defenses.css'

type DimensionFilter = DimensionId | 'all'

const DIMENSION_OPTIONS = [
  { value: 'all' as const, label: 'All' },
  ...DIMENSIONS.map((d) => ({ value: d.id, label: d.label })),
]

/** Most under-solved category first (solution − concern, ascending). */
const ROWS = [...DEFENSES].sort((a, b) => getShare(a.category).gap - getShare(b.category).gap)

export function Defenses() {
  const [dimension, setDimension] = useState<DimensionFilter>('all')
  const [selected, setSelected] = useState<ReadonlySet<CategoryId>>(new Set())

  const visibleCategories = CATEGORIES.filter(
    (c) => dimension === 'all' || c.dimension === dimension,
  )
  const rows = ROWS.filter((row) => {
    const category = getCategory(row.category)
    if (dimension !== 'all' && category.dimension !== dimension) return false
    return selected.size === 0 || selected.has(row.category)
  })

  const toggleCategory = (id: CategoryId) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  const changeDimension = (value: DimensionFilter) => {
    setDimension(value)
    // Drop category picks that the new dimension hides.
    setSelected(
      new Set(
        [...selected].filter((id) => value === 'all' || getCategory(id).dimension === value),
      ),
    )
  }

  const clear = () => {
    setDimension('all')
    setSelected(new Set())
  }

  return (
    <div className="defenses">
      <div className="filters" role="search" aria-label="Filter the defense matrix">
        <div className="filters__row">
          <span className="filters__label">
            Dimension
          </span>
          <SegmentedControl
            label="Dimension"
            options={DIMENSION_OPTIONS}
            value={dimension}
            onChange={changeDimension}
          />
        </div>
        <div className="filters__row">
          <span className="filters__label">Category</span>
          <div className="chip-toggles" role="group" aria-label="Category">
            {visibleCategories.map((c) => (
              <button
                key={c.id}
                type="button"
                className={cx('chip-toggle', c.id === UNDER_SOLVED && 'chip-toggle--highlight')}
                aria-pressed={selected.has(c.id)}
                onClick={() => toggleCategory(c.id)}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>
        <div className="filters__summary">
          <span aria-live="polite">
            Showing {rows.length} of {DEFENSES.length} categories
          </span>
          {(dimension !== 'all' || selected.size > 0) && (
            <button type="button" className="btn btn--ghost" onClick={clear}>
              Clear filters
            </button>
          )}
        </div>
      </div>

      <div className="matrix" role="table" aria-label="Threat to defense matrix">
        <div className="matrix__head" role="row">
          <span role="columnheader">Concern category</span>
          <span role="columnheader">Citations (Figs 6 &amp; 8)</span>
          <span role="columnheader">Defenses</span>
        </div>
        {rows.map((row) => {
          const category = getCategory(row.category)
          const share = getShare(row.category)
          const gap = row.category === UNDER_SOLVED
          return (
            <div key={row.category} className={cx('matrix__row', gap && 'is-gap')} role="row">
              <div className="matrix__category" role="rowheader">
                <h3>{category.label}</h3>
                <span className="badge">{getDimension(category.dimension).label}</span>
                {gap && <span className="badge badge--highlight">The gap</span>}
              </div>
              <div className="matrix__share" role="cell">
                <span>
                  Concern <strong className="num">{share.concern}%</strong>
                </span>
                <span>
                  Solution <strong className="num">{share.solution}%</strong>
                </span>
                <span className={cx('matrix__gap', share.gap < 0 && 'is-negative')}>
                  Gap <strong className="num">{formatGap(share.gap)}</strong>
                </span>
              </div>
              <ul className="matrix__controls" role="cell">
                {row.controls.map((control) => (
                  <li key={control}>{control}</li>
                ))}
              </ul>
            </div>
          )
        })}
        {rows.length === 0 && (
          <p className="matrix__empty">No categories match these filters.</p>
        )}
      </div>

      <p className="figure-caption">
        <strong>Sources:</strong> concern categories and citation shares from Gonzalez et al.
        (2012), Figures 6 &amp; 8. The defenses are current, published best practice that answer
        each concern — they are not taken from the paper. Sorted with the most under-solved
        category first.
      </p>
    </div>
  )
}
