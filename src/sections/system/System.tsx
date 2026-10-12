import { DEFENSES } from '../../data/defenses'
import { VIRTUALIZATION_DEFENSE_NOTES } from '../../data/defenseNotes'
import { PROFILE_ROWS, RUN_COMMANDS } from '../../data/system'
import { useChartColors } from '../../hooks/useChartColors'
import { ArchitectureDiagram } from './ArchitectureDiagram'
import { CheckCatalogue } from './CheckCatalogue'
import './System.css'

const VIRT_CONTROLS = DEFENSES.find((d) => d.category === 'virtualization')!.controls

export function System() {
  const c = useChartColors()
  return (
    <div className="system">
      <figure className="card system__figure">
        <ArchitectureDiagram />
        <figcaption className="figure-caption">
          R badges show which of the paper’s requirements each component serves. CPU layout from the
          published run’s placement plan (<code>lab.py cpus</code>), which reads the host’s real
          core/thread topology.
        </figcaption>
      </figure>

      <section className="card system__block" aria-labelledby="profiles-heading">
        <h3 id="profiles-heading" className="card__title">
          Two profiles, one provider plane
        </h3>
        <p className="card__subtitle">
          The same three workloads, deployed twice: a deliberately weak lift-and-shift baseline, and with
          the paper-derived controls. Only the tenant settings differ.
        </p>
        <div className="data-table__wrap">
          <table className="data-table data-table--prose system__profiles">
            <thead>
              <tr>
                <th scope="col">Aspect</th>
                <th scope="col">
                  <span className="system__key" style={{ background: c.insecure }} aria-hidden="true" />
                  Insecure
                </th>
                <th scope="col">
                  <span className="system__key" style={{ background: c.hardened }} aria-hidden="true" />
                  Hardened
                </th>
                <th scope="col">Req</th>
              </tr>
            </thead>
            <tbody>
              {PROFILE_ROWS.map((r) => (
                <tr key={r.aspect}>
                  <th scope="row">{r.aspect}</th>
                  <td data-label="Insecure">{r.insecure}</td>
                  <td data-label="Hardened">{r.hardened}</td>
                  <td data-label="Requirement">{r.requirement}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card system__block" aria-labelledby="checks-heading">
        <h3 id="checks-heading" className="card__title">
          The auditor’s 30 checks
        </h3>
        <p className="card__subtitle">
          Each check targets one of Figure 11’s sub-issues, serves one or more requirements, and is
          traced to the paper’s taxonomy and frameworks, so a finding reads in the paper’s own terms.
          Open a row for what it checks and how to fix it.
        </p>
        <CheckCatalogue />
      </section>

      <section className="card system__block" aria-labelledby="defenses-heading">
        <h3 id="defenses-heading" className="card__title">
          Virtualization defenses: which ones IsoLab implements
        </h3>
        <p className="card__subtitle">
          The standard defenses for the virtualization gap, and the checks that enforce or verify them in
          the testbed. Where one is out of reach, it says why.
        </p>
        <div className="data-table__wrap">
          <table className="data-table data-table--prose">
            <thead>
              <tr>
                <th scope="col">Defense</th>
                <th scope="col">Implemented by</th>
              </tr>
            </thead>
            <tbody>
              {VIRT_CONTROLS.map((control) => {
                const note = VIRTUALIZATION_DEFENSE_NOTES[control]
                return (
                  <tr key={control}>
                    <th scope="row">
                      {control}
                      <span className="system__aim">{note.aim}</span>
                    </th>
                    <td>
                      {note.implementedBy.length > 0 && (
                        <span className="system__ids">
                          {note.implementedBy.map((id) => (
                            <code key={id}>{id}</code>
                          ))}
                        </span>
                      )}
                      {note.outOfScope && <p className="system__scope">{note.outOfScope}</p>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card system__block" aria-labelledby="run-heading">
        <h3 id="run-heading" className="card__title">
          Run it
        </h3>
        <p className="card__subtitle">
          Everything is driven by one standard-library script; the auditor runs in its own container. CI
          runs the same commands on every push and refuses to deploy if the hardened gate fails.
        </p>
        <pre className="system__code">
          <code>{RUN_COMMANDS}</code>
        </pre>
      </section>
    </div>
  )
}
