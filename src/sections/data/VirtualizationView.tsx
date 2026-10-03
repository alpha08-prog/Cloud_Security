import { ChartCard, DataTable, SeriesLegend, type Column } from '../../components/charts/ChartCard'
import type { GapRow } from '../../components/charts/GapChart'
import { PairedBarChart } from '../../components/charts/PairedBarChart'
import { PairedRadarChart } from '../../components/charts/PairedRadarChart'
import { VIRTUALIZATION_RADAR_MAX } from '../../data/stats'
import { useChartColors } from '../../hooks/useChartColors'
import { VIRTUALIZATION_ROWS } from '../../lib/chartRows'

const differences = VIRTUALIZATION_ROWS.map((r) => r.concern - r.solution)
const allUnderSolved = differences.every((d) => d > 0)
const minSolution = Math.min(...VIRTUALIZATION_ROWS.map((r) => r.solution))
const leastSolved = VIRTUALIZATION_ROWS.filter((r) => r.solution === minSolution).map((r) => r.label)

const COLUMNS: readonly Column<GapRow>[] = [
  { header: 'Sub-issue', cell: (r) => r.label },
  { header: 'Concern', cell: (r) => r.concern, numeric: true },
  { header: 'Solution', cell: (r) => r.solution, numeric: true },
  { header: 'Concern − solution', cell: (r) => r.concern - r.solution, numeric: true },
]

const CAPTION = (
  <>
    <strong>Source:</strong> Gonzalez et al. (2012), Figure 11. <strong>Approximate</strong> —
    values read from the figure, on its own scale of roughly 0–{VIRTUALIZATION_RADAR_MAX}.
  </>
)

export function VirtualizationView() {
  const c = useChartColors()
  const legend = (
    <SeriesLegend
      items={[
        { label: 'Concern', color: c.concern, shape: 'line' },
        { label: 'Solution', color: c.solution, shape: 'line' },
      ]}
    />
  )
  const table = <DataTable rows={VIRTUALIZATION_ROWS} columns={COLUMNS} rowKey={(r) => r.key} />

  return (
    <div className="data-view">
      {allUnderSolved && (
        <div className="callout callout--highlight">
          <p>
            Inside virtualization, concern outweighs solution on all {VIRTUALIZATION_ROWS.length}{' '}
            sub-issues — by {Math.min(...differences)} to {Math.max(...differences)} points on the
            figure’s scale.
          </p>
          <p>
            Least solution coverage ({minSolution} on the scale): {leastSolved.join(', ')}.
            Cross-VM attacks are the subject of the Side-channel simulator.
          </p>
        </div>
      )}

      <div className="data-grid">
        <ChartCard
          title="Virtualization sub-issues (radar)"
          subtitle="Concern vs solution for each virtualization sub-issue, as in the paper’s radar."
          legend={legend}
          caption={CAPTION}
          table={table}
        >
          <PairedRadarChart
            rows={VIRTUALIZATION_ROWS}
            max={VIRTUALIZATION_RADAR_MAX}
            tickCount={6}
            unit=""
          />
        </ChartCard>

        <ChartCard
          title="Same values as bars"
          subtitle="Bars make the size of each gap easier to compare than the radar."
          legend={
            <SeriesLegend
              items={[
                { label: 'Concern', color: c.concern },
                { label: 'Solution', color: c.solution },
              ]}
            />
          }
          caption={CAPTION}
        >
          <PairedBarChart
            rows={VIRTUALIZATION_ROWS}
            max={VIRTUALIZATION_RADAR_MAX}
            ticks={[0, 5, 10, 15, 20, 25]}
            unit=""
            xLabel="Figure 11 scale (approximate)"
            yLabel="Sub-issue"
            labelWidth={168}
            rowHeight={40}
          />
        </ChartCard>
      </div>
    </div>
  )
}
