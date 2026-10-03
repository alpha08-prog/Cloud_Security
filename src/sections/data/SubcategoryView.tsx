import { ChartCard, DataTable, SeriesLegend, type Column } from '../../components/charts/ChartCard'
import type { GapRow } from '../../components/charts/GapChart'
import { PairedBarChart } from '../../components/charts/PairedBarChart'
import { categoryOfSubcategory, getCategory } from '../../data/taxonomy'
import { useChartColors } from '../../hooks/useChartColors'
import { SUBCATEGORY_ROWS, largestDeficit } from '../../lib/chartRows'
import { formatGap } from '../../lib/format'

const categoryLabel = (name: string) => {
  const id = categoryOfSubcategory(name)
  return id ? getCategory(id).label : 'Not a node in the taxonomy trees'
}

const worst = largestDeficit(SUBCATEGORY_ROWS)
const concernTotal = SUBCATEGORY_ROWS.reduce((sum, r) => sum + r.concern, 0)
const solutionTotal = SUBCATEGORY_ROWS.reduce((sum, r) => sum + r.solution, 0)

const COLUMNS: readonly Column<GapRow>[] = [
  { header: 'Sub-category', cell: (r) => r.label },
  { header: 'Category (from trees)', cell: (r) => categoryLabel(r.label) },
  { header: 'Concern %', cell: (r) => r.concern, numeric: true },
  { header: 'Solution %', cell: (r) => r.solution, numeric: true },
  { header: 'Gap (pts)', cell: (r) => formatGap(r.gap, ''), numeric: true },
]

export function SubcategoryView() {
  const c = useChartColors()

  return (
    <div className="data-view">
      <div className="callout callout--highlight">
        <p>
          Largest sub-category deficit: <strong>{worst.label}</strong> — {worst.concern}% of
          concerns vs {worst.solution}% of solutions ({formatGap(worst.gap)}), in the{' '}
          {categoryLabel(worst.label)} branch. Virtualization sub-categories are shaded.
        </p>
      </div>

      <ChartCard
        title="Concern vs solution, by sub-category"
        subtitle="Finer-grained breakdown of the same citations. Sorted by concern share."
        legend={
          <SeriesLegend
            items={[
              { label: 'Concern (Fig 5)', color: c.concern },
              { label: 'Solution (Fig 7)', color: c.solution },
            ]}
          />
        }
        caption={
          <>
            <strong>Source:</strong> Gonzalez et al. (2012), Figure 5 (concerns) and Figure 7
            (solutions). <strong>Approximate</strong> — values read from the charts, so the columns
            sum to {concernTotal}% and {solutionTotal}%. Categories are matched by name to the
            taxonomy trees (Figures 2–4).
          </>
        }
        table={<DataTable rows={SUBCATEGORY_ROWS} columns={COLUMNS} rowKey={(r) => r.key} />}
      >
        <PairedBarChart
          rows={SUBCATEGORY_ROWS}
          max={12}
          ticks={[0, 3, 6, 9, 12]}
          xLabel="Share of citations (%, approximate)"
          yLabel="Sub-category"
          labelWidth={176}
          rowHeight={30}
          tooltipFooter={categoryLabel}
        />
      </ChartCard>
    </div>
  )
}
