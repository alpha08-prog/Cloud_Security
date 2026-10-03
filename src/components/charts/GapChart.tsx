import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Rectangle,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
  type BarShapeProps,
  type YAxisTickContentProps,
} from 'recharts'
import { useChartColors } from '../../hooks/useChartColors'
import { formatGap } from '../../lib/format'
import { CategoryTick } from './PairedBarChart'

export interface GapRow {
  key: string
  label: string
  concern: number
  solution: number
  gap: number
  highlight?: boolean
}

interface GapChartProps {
  rows: readonly GapRow[]
  /** Symmetric axis bound in percentage points. */
  bound: number
  xLabel: string
  yLabel: string
}

/**
 * Diverging bars of solution − concern. One highlighted row carries the story;
 * the rest stay neutral gray (emphasis, not a categorical palette).
 */
export function GapChart({ rows, bound, xLabel, yLabel }: GapChartProps) {
  const c = useChartColors()
  const height = rows.length * 30 + 76

  const gapLabel = (props: { viewBox?: unknown; value?: unknown; index?: number }) => {
    const { x, width, y, height } = props.viewBox as {
      x: number
      y: number
      width: number
      height: number
    }
    const value = Number(props.value)
    const left = Math.min(x, x + width)
    const right = Math.max(x, x + width)
    const highlight = props.index !== undefined && rows[props.index]?.highlight
    return (
      <text
        x={value < 0 ? left - 6 : right + 6}
        y={y + height / 2}
        dy={4}
        textAnchor={value < 0 ? 'end' : 'start'}
        fill={highlight ? c.text : c.textMuted}
        fontSize={12}
        fontWeight={highlight ? 650 : 400}
      >
        {formatGap(value, '')}
      </text>
    )
  }

  return (
    <BarChart
      layout="vertical"
      data={rows as GapRow[]}
      responsive
      style={{ width: '100%', height }}
      margin={{ top: 24, right: 32, bottom: 28, left: 0 }}
      barCategoryGap="28%"
    >
      <CartesianGrid horizontal={false} stroke={c.grid} />
      <XAxis
        type="number"
        domain={[-bound, bound]}
        ticks={[-bound, -bound / 2, 0, bound / 2, bound]}
        tickFormatter={(v: number) => formatGap(v, '')}
        stroke={c.axis}
        tick={{ fill: c.textMuted, fontSize: 12 }}
        tickLine={false}
        label={{ value: xLabel, position: 'insideBottom', offset: -18, fill: c.textMuted, fontSize: 12 }}
      />
      <YAxis
        type="category"
        dataKey="label"
        width={128}
        interval={0}
        tickLine={false}
        axisLine={false}
        tick={(props: YAxisTickContentProps) => (
          <CategoryTick {...props} colors={c} highlight={rows[props.index]?.highlight} />
        )}
        label={{ value: yLabel, position: 'top', offset: 10, fill: c.textMuted, fontSize: 12 }}
      />
      <ReferenceLine x={0} stroke={c.axis} />
      <Tooltip
        cursor={{ fill: c.grid }}
        content={({ active, payload }) => {
          const row = payload?.[0]?.payload as GapRow | undefined
          if (!active || !row) return null
          return (
            <div className="chart-tooltip">
              <p className="chart-tooltip__title">{row.label}</p>
              <p style={{ margin: 0 }}>
                <strong className="num">{formatGap(row.gap)}</strong>{' '}
                <span style={{ color: 'var(--text-muted)' }}>gap</span>
              </p>
              <div className="chart-tooltip__footer">
                Concern {row.concern}% · Solution {row.solution}%
              </div>
            </div>
          )
        }}
      />
      <Bar
        dataKey="gap"
        name="Gap"
        barSize={14}
        radius={[0, 4, 4, 0]}
        shape={(props: BarShapeProps) => {
          // Normalise negative widths so the rounded end always points away from zero.
          const negative = props.width < 0
          return (
            <Rectangle
              {...props}
              x={negative ? props.x + props.width : props.x}
              width={Math.abs(props.width)}
              radius={negative ? [4, 0, 0, 4] : [0, 4, 4, 0]}
              fill={(props.payload as GapRow).highlight ? c.highlight : c.muted}
            />
          )
        }}
      >
        <LabelList dataKey="gap" content={gapLabel} />
      </Bar>
    </BarChart>
  )
}
