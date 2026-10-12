import { useState } from 'react'
import { ChartCard, DataTable, SeriesLegend, type Column } from '../../components/charts/ChartCard'
import { PairedRadarChart, SeriesRadarChart } from '../../components/charts/PairedRadarChart'
import { SegmentedControl } from '../../components/SegmentedControl'
import { StatusBadge } from '../../components/StatusBadge'
import { AXES, AXIS_LABEL, type AxisInfo } from '../../data/axes'
import type { Axis, ProfileName } from '../../data/resultTypes'
import { AUDITS, CATALOGUE, CHECK_BY_ID, PROFILE_LABEL } from '../../data/results'
import { VIRTUALIZATION_RADAR_MAX } from '../../data/stats'
import { useChartColors } from '../../hooks/useChartColors'
import { VIRTUALIZATION_ROWS } from '../../lib/chartRows'
import { pct } from '../../lib/evidence'

const score = (p: ProfileName, axis: Axis) => AUDITS[p].scores.byAxis.find((s) => s.key === axis)!

const COVERAGE_ROWS = AXES.map((a) => ({
  key: a.id,
  label: a.label,
  insecure: Math.round((score('insecure', a.id).score ?? 0) * 100),
  hardened: Math.round((score('hardened', a.id).score ?? 0) * 100),
}))

const AXIS_COLUMNS: readonly Column<AxisInfo>[] = [
  { header: 'Figure 11 sub-issue', cell: (a) => a.label },
  { header: 'Paper: concern', cell: (a) => a.paperConcern, numeric: true },
  { header: 'Paper: solution', cell: (a) => a.paperSolution, numeric: true },
  { header: 'Checks', cell: (a) => CATALOGUE.filter((c) => c.axis === a.id).length, numeric: true },
  { header: 'Insecure', cell: (a) => pct(score('insecure', a.id).score), numeric: true },
  { header: 'Hardened', cell: (a) => pct(score('hardened', a.id).score), numeric: true },
  {
    header: 'Evaluated',
    cell: (a) => {
      const s = score('hardened', a.id)
      return `${s.evaluated} of ${s.total}`
    },
    numeric: true,
  },
]

type Show = 'issues' | 'all'

export function AuditView() {
  const c = useChartColors()
  const [profile, setProfile] = useState<ProfileName>('hardened')
  const [show, setShow] = useState<Show>('issues')
  const report = AUDITS[profile]
  const rows = report.results.filter((r) => show === 'all' || r.status !== 'pass')

  return (
    <div className="results__view">
      <div className="data-grid results__fig11">
        <ChartCard
          title="A · The paper: Figure 11"
          subtitle="How often 2012 literature raised (concern) or answered (solution) each virtualization sub-issue."
          legend={
            <SeriesLegend
              items={[
                { label: 'Concern', color: c.concern, shape: 'line' },
                { label: 'Solution', color: c.solution, shape: 'line' },
              ]}
            />
          }
          caption={
            <>
              <strong>Source:</strong> Gonzalez et al. (2012), Figure 11, approximate citation counts.
            </>
          }
        >
          <PairedRadarChart rows={VIRTUALIZATION_ROWS} max={VIRTUALIZATION_RADAR_MAX} tickCount={6} unit="" />
        </ChartCard>
        <ChartCard
          title="B · Figure 11, revisited: IsoLab coverage"
          subtitle="Severity-weighted share of the auditor’s checks that pass, per sub-issue, in each profile."
          legend={
            <SeriesLegend
              items={[
                { label: 'Insecure', color: c.insecure, shape: 'line' },
                { label: 'Hardened', color: c.hardened, shape: 'line' },
              ]}
            />
          }
          caption={
            <>
              <strong>Different units.</strong> A counts citations; B is coverage (0–100%). Compare shapes,
              not values. The hypervisor axis stays lowest even when hardened: two host issues (CPU microcode,
              user namespaces) are the provider’s to fix and are waived, which earns no credit.
            </>
          }
          table={<DataTable rows={AXES} columns={AXIS_COLUMNS} rowKey={(a) => a.id} />}
        >
          <SeriesRadarChart
            rows={COVERAGE_ROWS}
            series={[
              { key: 'insecure', name: 'Insecure', color: c.insecure },
              { key: 'hardened', name: 'Hardened', color: c.hardened },
            ]}
            max={100}
            tickCount={5}
            unit="%"
          />
        </ChartCard>
      </div>

      <section className="card results__block" aria-labelledby="findings-heading">
        <div className="results__block-head">
          <div>
            <h3 id="findings-heading" className="card__title">
              Findings
            </h3>
            <p className="card__subtitle">
              Every check’s outcome. The same results are exported as SARIF for GitHub code scanning, pointing
              at the compose line to fix.
            </p>
          </div>
          <div className="toolbar__group">
            <SegmentedControl
              label="Profile"
              options={[
                { value: 'hardened', label: PROFILE_LABEL.hardened },
                { value: 'insecure', label: PROFILE_LABEL.insecure },
              ]}
              value={profile}
              onChange={setProfile}
            />
            <SegmentedControl
              label="Show"
              options={[
                { value: 'issues', label: 'Not passing' },
                { value: 'all', label: 'All 30' },
              ]}
              value={show}
              onChange={setShow}
            />
          </div>
        </div>
        <div className="data-table__wrap">
          <table className="data-table data-table--prose results__findings">
            <thead>
              <tr>
                <th scope="col">Status</th>
                <th scope="col">Check</th>
                <th scope="col">Axis</th>
                <th scope="col">Finding</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const spec = CHECK_BY_ID.get(r.checkId)!
                return (
                  <tr key={r.checkId}>
                    <td>
                      <StatusBadge status={r.status} note={r.waived ? 'waived' : undefined} />
                    </td>
                    <td>
                      <code>{r.checkId}</code> {spec.title}
                      <span className="results__severity">{spec.severity}</span>
                    </td>
                    <td>{AXIS_LABEL[spec.axis]}</td>
                    <td className="results__message">
                      {r.message}
                      {r.waived && r.waiver && <span className="results__waiver">Waived: {r.waiver.reason}</span>}
                    </td>
                  </tr>
                )
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={4}>Every check passes.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
