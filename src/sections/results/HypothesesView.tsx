import { StatusBadge } from '../../components/StatusBadge'
import type { Verdict } from '../../data/resultTypes'
import { E1, E2, E3 } from '../../data/results'

const BADGE: Record<Verdict, { status: 'pass' | 'fail' | 'skip'; label: string }> = {
  supported: { status: 'pass', label: 'Supported' },
  'not-supported': { status: 'fail', label: 'Not supported' },
  inconclusive: { status: 'skip', label: 'Inconclusive' },
}

const GROUPS = [
  { experiment: 'E1 · Noisy neighbour', hypotheses: E1.hypotheses },
  { experiment: 'E2 · Segmentation', hypotheses: E2.hypotheses },
  { experiment: 'E3 · Detection', hypotheses: E3.hypotheses },
]

export function HypothesesView() {
  return (
    <div className="results__view">
      <p className="results__lede">
        The hypotheses and pass criteria were written down before any experiment ran (docs/experiments.md), and
        any later protocol change is logged there with its reason. Verdicts are computed by{' '}
        <code>lab.py publish</code>, not chosen by hand.
      </p>
      {GROUPS.map((g) => (
        <section key={g.experiment} className="card results__block">
          <h3 className="card__title">{g.experiment}</h3>
          <ul className="results__hypotheses">
            {g.hypotheses.map((h) => (
              <li key={h.id}>
                <StatusBadge status={BADGE[h.verdict].status} label={`${h.id} · ${BADGE[h.verdict].label}`} />
                <div>
                  <p>{h.statement}</p>
                  <p className="results__muted">{h.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
