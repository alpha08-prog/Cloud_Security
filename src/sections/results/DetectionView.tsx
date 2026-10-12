import { ChartCard, SeriesLegend } from '../../components/charts/ChartCard'
import { ProfileBarChart, type ProfileRow } from '../../components/charts/ProfileBarChart'
import { StatusBadge } from '../../components/StatusBadge'
import { DETECTION_RULES } from '../../data/requirements'
import type { ProfileName } from '../../data/resultTypes'
import { E3, PROFILES, PROFILE_LABEL } from '../../data/results'
import { useChartColors } from '../../hooks/useChartColors'
import { ms } from '../../lib/evidence'

const result = (p: ProfileName, id: string) => E3.results.find((r) => r.profile === p && r.triggerId === id)

// The noisy-neighbour trigger is measured in tens of seconds (it must persist 30 s by
// design), so it is reported in text rather than squashing the sub-second bars.
const FAST = E3.triggers.filter((t) => t.id !== 'T7')
const ROWS: ProfileRow[] = FAST.map((t) => ({
  key: t.id,
  label: `${t.id} · ${t.expectedRule}`,
  insecure: result('insecure', t.id)?.latencyMs ?? null,
  hardened: result('hardened', t.id)?.latencyMs ?? null,
}))
const MAX = Math.ceil((Math.max(...ROWS.flatMap((r) => [r.insecure ?? 0, r.hardened ?? 0])) * 1.2) / 50) * 50

export function DetectionView() {
  const c = useChartColors()
  const t7 = E3.triggers.find((t) => t.id === 'T7')

  return (
    <div className="results__view">
      <p className="results__lede">
        First a {E3.quietWindowSeconds}-second quiet window under normal traffic: any alert there is a false
        positive. Then benign triggers, harmless commands shaped like isolation-breaking actions (the idea behind
        Falco’s event generator), each expected to raise one specific detection, attributed to the right tenant,
        within its SLO.
      </p>

      <div className="data-grid">
        <ChartCard
          title="Time from action to detection"
          subtitle="Measured on the host’s own clock: engine event time → alert time. SLO 5 s."
          legend={
            <SeriesLegend
              items={[
                { label: 'Insecure', color: c.insecure },
                { label: 'Hardened', color: c.hardened },
              ]}
            />
          }
          caption={
            <>
              <strong>Source:</strong> experiment E3. {t7?.id} (noisy neighbour, DET-08) is not drawn: it must hold for
              30 s by design: {ms(result('insecure', 'T7')?.latencyMs)} in the insecure profile, silent when hardened.
            </>
          }
        >
          <ProfileBarChart rows={ROWS} max={MAX} unit="ms" xLabel="Detection latency (ms)" yLabel="Trigger" decimals={0} />
        </ChartCard>

        <div className="results__side">
          {PROFILES.map((p) => {
            const s = E3.summary.find((x) => x.profile === p)!
            return (
              <div key={p} className="card results__factor">
                <p className="eyebrow">
                  <span className="results__key" style={{ background: p === 'insecure' ? c.insecure : c.hardened }} />
                  {PROFILE_LABEL[p]}
                </p>
                <p className="results__factor-value">
                  {s.detected}/{s.expected}
                </p>
                <p className="results__factor-note">
                  detected in SLO · {s.falsePositives} false positives · attribution{' '}
                  {s.attributionAccuracy === null ? '–' : `${Math.round(s.attributionAccuracy * 100)}%`}
                </p>
              </div>
            )
          })}
        </div>
      </div>

      <div className="data-table__wrap card">
        <table className="data-table data-table--prose">
          <thead>
            <tr>
              <th scope="col">Trigger</th>
              <th scope="col">Expected detection</th>
              {PROFILES.map((p) => (
                <th key={p} scope="col">
                  {PROFILE_LABEL[p]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {E3.triggers.map((t) => (
              <tr key={t.id}>
                <th scope="row">
                  <code>{t.id}</code> {t.description}
                </th>
                <td>
                  <code>{t.expectedRule}</code> {DETECTION_RULES[t.expectedRule]}
                </td>
                {PROFILES.map((p) => {
                  const r = result(p, t.id)
                  if (!r) return <td key={p}>–</td>
                  if (r.expected === 'silent') {
                    return (
                      <td key={p}>
                        <StatusBadge status={r.asExpected ? 'pass' : 'fail'} label={r.asExpected ? 'Silent' : 'Fired'} />
                        <span className="results__detail">no noisy neighbour possible</span>
                      </td>
                    )
                  }
                  return (
                    <td key={p}>
                      <StatusBadge status={r.asExpected ? 'pass' : 'fail'} label={r.detected ? ms(r.latencyMs) : 'Missed'} />
                      <span className="results__detail">tenant: {r.tenant ?? 'unattributed'}</span>
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
