import { useState } from 'react'
import { SegmentedControl } from '../../components/SegmentedControl'
import { AXES, AXIS_LABEL } from '../../data/axes'
import { FRAMEWORKS } from '../../data/frameworks'
import type { Axis, RequirementId } from '../../data/resultTypes'
import { CATALOGUE } from '../../data/results'
import { TAXONOMY_FIGURES, indexFigure } from '../../data/taxonomy'
import { cx } from '../../lib/format'

const NODE_PATH = new Map<string, string>()
for (const figure of TAXONOMY_FIGURES.slice(1)) {
  for (const [id, ctx] of indexFigure(figure)) {
    NODE_PATH.set(id, ctx.path.map((n) => n.label).join(' › '))
  }
}

const THREATS = FRAMEWORKS.find((f) => f.id === 'csa-top-threats')!.lists![0].items

const AXIS_OPTIONS = [
  { value: 'all' as const, label: 'All' },
  ...AXES.map((a) => ({ value: a.id, label: a.label })),
]
const REQS: RequirementId[] = ['R1', 'R2', 'R3', 'R4']

/** The auditor's 30 checks, each traced to the paper's taxonomy and frameworks. */
export function CheckCatalogue() {
  const [axis, setAxis] = useState<Axis | 'all'>('all')
  const [reqs, setReqs] = useState<ReadonlySet<RequirementId>>(new Set())

  const rows = CATALOGUE.filter(
    (c) => (axis === 'all' || c.axis === axis) && (reqs.size === 0 || c.requirements.some((r) => reqs.has(r))),
  )
  const toggle = (r: RequirementId) => {
    const next = new Set(reqs)
    if (next.has(r)) next.delete(r)
    else next.add(r)
    setReqs(next)
  }

  return (
    <div className="catalogue">
      <div className="filters" role="search" aria-label="Filter the check catalogue">
        <div className="filters__row">
          <span className="filters__label">Figure 11 axis</span>
          <SegmentedControl label="Axis" options={AXIS_OPTIONS} value={axis} onChange={setAxis} />
        </div>
        <div className="filters__row">
          <span className="filters__label">Requirement</span>
          <div className="chip-toggles" role="group" aria-label="Requirement">
            {REQS.map((r) => (
              <button
                key={r}
                type="button"
                className="chip-toggle"
                aria-pressed={reqs.has(r)}
                onClick={() => toggle(r)}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        <p className="filters__summary">
          {rows.length} of {CATALOGUE.length} checks
        </p>
      </div>

      <div className="data-table__wrap">
        <table className="data-table data-table--prose catalogue__table">
          <thead>
            <tr>
              <th scope="col">Check</th>
              <th scope="col">Axis · requirement</th>
              <th scope="col">Paper taxonomy (Figs 2–4)</th>
              <th scope="col">Frameworks</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td>
                  <details className="catalogue__details">
                    <summary>
                      <code>{c.id}</code> {c.title}{' '}
                      <span className={cx('badge', (c.severity === 'critical' || c.severity === 'high') && 'badge--highlight')}>
                        {c.severity}
                      </span>
                    </summary>
                    <p>{c.description}</p>
                    <p>
                      <strong>Fix:</strong> {c.remediation}
                    </p>
                    {c.platformNotes && <p className="catalogue__note">{c.platformNotes}</p>}
                  </details>
                </td>
                <td>
                  {AXIS_LABEL[c.axis]}
                  <br />
                  <span className="catalogue__muted">{c.requirements.join(' · ')}</span>
                </td>
                <td>
                  <ul className="catalogue__nodes">
                    {c.taxonomy.map((t) => (
                      <li key={t}>{NODE_PATH.get(t) ?? t}</li>
                    ))}
                  </ul>
                </td>
                <td className="catalogue__fw">
                  {c.frameworks.csaTopThreats.map((t) => (
                    <span key={t} title={THREATS[t - 1]}>
                      CSA #{t}{' '}
                    </span>
                  ))}
                  <br />
                  <span className="catalogue__muted">
                    ENISA {c.frameworks.enisa.join(', ')} · NIST {c.frameworks.nist.join(', ')}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
