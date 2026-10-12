import { DETECTION_RULES, REQUIREMENTS } from '../../data/requirements'
import { CATALOGUE, PROFILES, PROFILE_LABEL } from '../../data/results'
import { useChartColors } from '../../hooks/useChartColors'
import { EVIDENCE, pct, requirementScore } from '../../lib/evidence'
import { QuoteWithRequirements } from './Quote'
import './Requirements.css'

export function Requirements() {
  const c = useChartColors()
  const swatch = { insecure: c.insecure, hardened: c.hardened }

  return (
    <div className="reqs">
      <QuoteWithRequirements />

      <div className="reqs__grid">
        {REQUIREMENTS.map((r) => {
          const checks = CATALOGUE.filter((x) => x.requirements.includes(r.id))
          return (
            <article key={r.id} className="card req" aria-labelledby={`req-${r.id}`}>
              <header className="req__head">
                <span className="req__id">{r.id}</span>
                <div>
                  <h3 id={`req-${r.id}`}>{r.short}</h3>
                  <p className="req__phrase">“{r.phrase}”</p>
                </div>
              </header>
              <p className="req__interp">{r.interpretation}</p>

              <div>
                <p className="eyebrow">How</p>
                <ul className="req__list">
                  {r.mechanisms.map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              </div>

              <div>
                <p className="eyebrow">Evidence</p>
                <ul className="req__list req__list--evidence">
                  {EVIDENCE[r.id].map((e) => (
                    <li key={e}>{e}</li>
                  ))}
                </ul>
              </div>

              <dl className="req__coverage">
                {PROFILES.map((p) => {
                  const s = requirementScore(p, r.id)
                  return (
                    <div key={p}>
                      <dt>
                        <span className="req__key" style={{ background: swatch[p] }} aria-hidden="true" />
                        {PROFILE_LABEL[p]}
                      </dt>
                      <dd className="num">{pct(s.score)}</dd>
                    </div>
                  )
                })}
                <p className="req__coverage-note">
                  coverage by {checks.length} static check{checks.length === 1 ? '' : 's'}
                  {r.coverageNote && <>. {r.coverageNote}</>}
                </p>
              </dl>
            </article>
          )
        })}
      </div>

      <section className="card reqs__trace" aria-labelledby="trace-heading">
        <h3 id="trace-heading" className="card__title">
          Traceability: requirement → mechanism → evidence
        </h3>
        <p className="card__subtitle">
          Static checks prove configuration; R3 and R4 are runtime properties, so their main evidence
          comes from detections and experiments.
        </p>
        <div className="data-table__wrap">
          <table className="data-table data-table--prose reqs__table">
            <thead>
              <tr>
                <th scope="col">Requirement</th>
                <th scope="col">Static checks</th>
                <th scope="col">Runtime detections</th>
                <th scope="col">Experiments</th>
              </tr>
            </thead>
            <tbody>
              {REQUIREMENTS.map((r) => (
                <tr key={r.id}>
                  <th scope="row">
                    {r.id} · {r.short}
                  </th>
                  <td>
                    <span className="reqs__ids">
                      {CATALOGUE.filter((x) => x.requirements.includes(r.id)).map((x) => (
                        <code key={x.id}>{x.id}</code>
                      ))}
                    </span>
                  </td>
                  <td>
                    <ul className="reqs__dets">
                      {r.detections.map((d) => (
                        <li key={d}>
                          <code>{d}</code> {DETECTION_RULES[d]}
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td>
                    {r.experiments.map((e) => (
                      <a key={e} className="badge badge--accent reqs__exp" href={`#results/${EXPERIMENT_VIEW[e]}`}>
                        {e}
                      </a>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <aside className="callout">
        <p>
          <strong>Why containers stand in for VMs.</strong> The CSA guidance reviewed by the paper (p.12)
          names multi-tenancy, not virtualization, as the essential cloud characteristic, and says
          segmentation and isolation are required either way. Containers share one kernel, so they are
          the harder isolation case: if the controls hold here, they are not relying on a hypervisor.
        </p>
      </aside>
    </div>
  )
}

const EXPERIMENT_VIEW = { E1: 'noisy', E2: 'segmentation', E3: 'detection' } as const
