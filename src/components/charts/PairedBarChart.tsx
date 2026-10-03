import type { ReactNode } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ReferenceArea,
  Tooltip,
  XAxis,
  YAxis,
  type YAxisTickContentProps,
} from 'recharts'
import { useChartColors, type ChartColors } from '../../hooks/useChartColors'
import { ChartTooltip } from './ChartCard'

export interface PairedRow {
  key: string
  label: string
  concern: number
  solution: number
  /** Row gets a tinted band, bold label and direct value labels. */
  highlight?: boolean
}

interface PairedBarChartProps {
  rows: readonly PairedRow[]
  /** Upper bound of the value axis. */
  max: number
  ticks?: number[]
  unit?: string
  xLabel: string
  yLabel: string
  labelWidth?: number
  rowHeight?: number
  tooltipFooter?: (label: string) => ReactNode
}

/** Horizontal concern-vs-solution bars, one pair per row. */
export function PairedBarChart({
  rows,
  max,
  ticks,
  unit = '%',
  xLabel,
  yLabel,
  labelWidth = 128,
  rowHeight = 34,
  tooltipFooter,
}: PairedBarChartProps) {
  const c = useChartColors()
  const height = rows.length * rowHeight + 76
  const isHighlight = (index?: number) => index !== undefined && rows[index]?.highlight

  const valueLabel = (props: { viewBox?: unknown; value?: unknown; index?: number }) => {
    if (!isHighlight(props.index)) return <g />
    const { x, y, width, height } = props.viewBox as Box
    return (
      <text x={x + width + 6} y={y + height / 2} dy={4} fill={c.text} fontSize={12} fontWeight={600}>
        {`${props.value}${unit}`}
      </text>
    )
  }

  return (
    <BarChart
      layout="vertical"
      data={rows as PairedRow[]}
      responsive
      style={{ width: '100%', height }}
      margin={{ top: 24, right: 40, bottom: 28, left: 0 }}
      barGap={2}
      barCategoryGap="20%"
    >
      <CartesianGrid horizontal={false} stroke={c.grid} />
      {rows
        .filter((r) => r.highlight)
        .map((r) => (
          <ReferenceArea
            key={r.key}
            y1={r.label}
            y2={r.label}
            fill={c.highlightSoft}
            fillOpacity={1}
            stroke="none"
          />
        ))}
      <XAxis
        type="number"
        domain={[0, max]}
        ticks={ticks}
        tickFormatter={(v: number) => `${v}${unit}`}
        stroke={c.axis}
        tick={{ fill: c.textMuted, fontSize: 12 }}
        tickLine={false}
        label={{ value: xLabel, position: 'insideBottom', offset: -18, fill: c.textMuted, fontSize: 12 }}
      />
      <YAxis
        type="category"
        dataKey="label"
        width={labelWidth}
        interval={0}
        tickLine={false}
        stroke={c.axis}
        tick={(props: YAxisTickContentProps) => (
          <CategoryTick {...props} colors={c} highlight={isHighlight(props.index)} />
        )}
        label={{ value: yLabel, position: 'top', offset: 10, fill: c.textMuted, fontSize: 12 }}
      />
      <Tooltip
        cursor={{ fill: c.grid }}
        content={(props) => <ChartTooltip {...props} unit={unit} footer={tooltipFooter} />}
      />
      <Bar dataKey="concern" name="Concern" fill={c.concern} barSize={10} radius={[0, 4, 4, 0]}>
        <LabelList dataKey="concern" content={valueLabel} />
      </Bar>
      <Bar dataKey="solution" name="Solution" fill={c.solution} barSize={10} radius={[0, 4, 4, 0]}>
        <LabelList dataKey="solution" content={valueLabel} />
      </Bar>
    </BarChart>
  )
}

interface Box {
  x: number
  y: number
  width: number
  height: number
}

export function CategoryTick({
  x,
  y,
  payload,
  colors,
  highlight,
}: YAxisTickContentProps & { colors: ChartColors; highlight?: boolean }) {
  return (
    <text
      x={Number(x) - 8}
      y={Number(y)}
      dy={4}
      textAnchor="end"
      fill={highlight ? colors.text : colors.textMuted}
      fontSize={12}
      fontWeight={highlight ? 650 : 400}
    >
      {String(payload.value)}
    </text>
  )
}
