import { StatusBadge } from '../../components/StatusBadge'
import { AXIS_LABEL } from '../../data/axes'
import type { ProfileName } from '../../data/resultTypes'
import { E2, PROFILES, PROFILE_LABEL } from '../../data/results'
import { e2Summary } from '../../lib/evidence'

const outcome = (profile: ProfileName, id: string) => E2.results.find((r) => r.profile === profile && r.probeId === id)

export function SegmentationView() {
  return (
    <div className="results__view">
      <p className="results__lede">
        From inside tenant C (and once from tenant B) we try every path out of a tenant: other tenants, the
        provider, the host, the internet, the engine. Every probe is read-only or a connection attempt with a
        2-second timeout. Three positive controls prove that “blocked” doesn’t just mean “the network is broken”.
      </p>

      <div className="results__summary-row">
        {PROFILES.map((p) => {
          const s = e2Summary(p)
          return (
            <div key={p} className="card results__summary">
              <p className="eyebrow">{PROFILE_LABEL[p]}</p>
              <p className="results__factor-value">
                {s?.openPaths} / {s?.probes}
              </p>
              <p className="results__factor-note">
                paths open · controls {s?.controlsPassed}/{s?.controls} reachable
              </p>
            </div>
          )
        })}
      </div>

      <div className="data-table__wrap card">
        <table className="data-table data-table--prose results__matrix">
          <thead>
            <tr>
              <th scope="col">Probe</th>
              <th scope="col">From → to</th>
              <th scope="col">Sub-issue</th>
              {PROFILES.map((p) => (
                <th key={p} scope="col">
                  {PROFILE_LABEL[p]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {E2.probes.map((probe) => (
              <tr key={probe.id} className={probe.control ? 'is-control' : undefined}>
                <th scope="row">
                  <code>{probe.id}</code> {probe.description}
                  {probe.control && <span className="badge">control</span>}
                </th>
                <td className="results__muted">
                  {probe.source} → {probe.destination}
                </td>
                <td className="results__muted">{AXIS_LABEL[probe.axis]}</td>
                {PROFILES.map((p) => {
                  const r = outcome(p, probe.id)
                  if (!r) return <td key={p}>–</td>
                  const status = probe.control
                    ? r.outcome === 'allowed'
                      ? 'control'
                      : 'fail'
                    : r.outcome === 'allowed'
                      ? 'open'
                      : 'blocked'
                  return (
                    <td key={p} title={r.detail}>
                      <StatusBadge status={status} label={status === 'fail' ? 'Broken' : undefined} />
                      <span className="results__detail">{r.detail}</span>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
