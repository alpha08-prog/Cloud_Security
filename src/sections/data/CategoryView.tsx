import { ChartCard, DataTable, SeriesLegend, type Column } from '../../components/charts/ChartCard'
import { GapChart, type GapRow } from '../../components/charts/GapChart'
import { PairedBarChart } from '../../components/charts/PairedBarChart'
import { PairedRadarChart } from '../../components/charts/PairedRadarChart'
import { StatTile } from '../../components/charts/StatTile'
import { getShare } from '../../data/stats'
import { CATEGORIES, UNDER_SOLVED, getCategory, getDimension } from '../../data/taxonomy'
import { useChartColors } from '../../hooks/useChartColors'
import { CATEGORY_ROWS, CATEGORY_ROWS_BY_GAP, largestDeficit } from '../../lib/chartRows'
import { formatGap } from '../../lib/format'

const underSolved = getShare(UNDER_SOLVED)
const worst = largestDeficit(CATEGORY_ROWS)

const dimensionOf = (label: string) =>
  getDimension(CATEGORIES.find((c) => c.label === label)!.dimension).label

const COLUMNS: readonly Column<GapRow>[] = [
  { header: 'Category', cell: (r) => r.label },
  { header: 'Dimension', cell: (r) => dimensionOf(r.label) },
  { header: 'Concern %', cell: (r) => r.concern, numeric: true },
  { header: 'Solution %', cell: (r) => r.solution, numeric: true },
  { header: 'Gap (pts)', cell: (r) => formatGap(r.gap, ''), numeric: true },
]

const SOURCE = 'Gonzalez et al. (2012), Figure 6 (concerns) and Figure 8 (solutions).'

export function CategoryView() {
  const c = useChartColors()
  const legend = (
    <SeriesLegend
      items={[
        { label: 'Concern (Fig 6)', color: c.concern },
        { label: 'Solution (Fig 8)', color: c.solution },
      ]}
    />
  )
  const table = <DataTable rows={CATEGORY_ROWS} columns={COLUMNS} rowKey={(r) => r.key} />

  return (
    <div className="data-view">
      <div className="stat-tiles">
        <StatTile
          label="Virtualization · share of concerns"
          value={`${underSolved.concern}%`}
          note="of concern citations (Fig 6)"
          swatch={c.concern}
        />
        <StatTile
          label="Virtualization · share of solutions"
          value={`${underSolved.solution}%`}
          note="of solution citations (Fig 8)"
          swatch={c.solution}
        />
        <StatTile
          label="Virtualization · coverage gap"
          value={formatGap(underSolved.gap)}
          note={
            <>
              {worst.key === UNDER_SOLVED
                ? 'The largest deficit of the seven categories'
                : `Largest deficit: ${worst.label}`}
              <br />
              <a className="link-cta" href="#side-channel">
                Why it matters: cross-VM side channels →
              </a>
            </>
          }
          highlight
        />
      </div>

      <div className="data-grid">
        <ChartCard
          title="Concern vs solution, by category"
          subtitle="Share of surveyed references that raise a concern vs propose a solution in each category. Sorted by concern share; each series sums to 100%."
          legend={legend}
          caption={
            <>
              <strong>Source:</strong> {SOURCE} Exact values.
            </>
          }
          table={table}
        >
          <PairedBarChart
            rows={CATEGORY_ROWS}
            max={30}
            ticks={[0, 10, 20, 30]}
            xLabel="Share of citations (%)"
            yLabel="Category"
            tooltipFooter={(label) => {
              const row = CATEGORY_ROWS.find((r) => r.label === label)
              return row && `Gap ${formatGap(row.gap)}`
            }}
          />
        </ChartCard>

        <ChartCard
          title="Radar overlay"
          subtitle="The same seven categories. Radius is share of citations; where the concern outline reaches past the solution outline, the category is under-solved."
          legend={legend}
          caption={
            <>
              <strong>Source:</strong> {SOURCE}
            </>
          }
        >
          <PairedRadarChart rows={CATEGORY_ROWS} max={30} />
        </ChartCard>
      </div>

      <ChartCard
        title="Coverage gap, by category"
        subtitle={`Solution share minus concern share. Negative means a category is raised more often than it is solved — ${getCategory(UNDER_SOLVED).label} is furthest below zero.`}
        caption={
          <>
            <strong>Source:</strong> computed from {SOURCE}
          </>
        }
        table={table}
      >
        <GapChart
          rows={CATEGORY_ROWS_BY_GAP}
          bound={12}
          xLabel="Gap in pts (solution − concern)"
          yLabel="Category"
        />
      </ChartCard>
    </div>
  )
}
