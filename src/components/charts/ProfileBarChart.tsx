import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
  type YAxisTickContentProps,
} from 'recharts'
import { useChartColors } from '../../hooks/useChartColors'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import { ChartTooltip } from './ChartCard'
import { CategoryTick } from './PairedBarChart'

export interface ProfileRow {
  key: string
  label: string
  insecure: number | null
  hardened: number | null
}

interface ProfileBarChartProps {
  rows: readonly ProfileRow[]
  max: number
  ticks?: number[]
  unit: string
  xLabel: string
  yLabel: string
  /** Optional threshold drawn across the plot (e.g. an SLO). */
  reference?: { value: number; label: string }
  labelWidth?: number
  rowHeight?: number
  decimals?: number
}

/**
 * Horizontal bars comparing the two IsoLab profiles on one value axis. Every bar
 * carries its value as a direct label (the light hardened colour is under 3:1).
 */
export function ProfileBarChart({
  rows,
  max,
  ticks,
  unit,
  xLabel,
  yLabel,
  reference,
  labelWidth = 150,
  rowHeight = 46,
  decimals = 1,
}: ProfileBarChartProps) {
  const c = useChartColors()
  const reduceMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const height = rows.length * rowHeight + 84
  const fmt = (v: unknown) => (typeof v === 'number' ? `${v.toFixed(decimals)} ${unit}` : '')

  const valueLabel = (props: { viewBox?: unknown; value?: unknown }) => {
    if (typeof props.value !== 'number') return <g />
    const { x, y, width, height } = props.viewBox as { x: number; y: number; width: number; height: number }
    return (
      <text x={x + width + 6} y={y + height / 2} dy={4} fill={c.text} fontSize={12} fontWeight={600}>
        {fmt(props.value)}
      </text>
    )
  }

  return (
    <BarChart
      layout="vertical"
      data={rows as ProfileRow[]}
      responsive
      style={{ width: '100%', height }}
      margin={{ top: 24, right: 64, bottom: 28, left: 0 }}
      barGap={2}
      barCategoryGap="22%"
    >
      <CartesianGrid horizontal={false} stroke={c.grid} />
      <XAxis
        type="number"
        domain={[0, max]}
        ticks={ticks}
        allowDataOverflow
        tickFormatter={(v: number) => `${v}`}
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
        tick={(props: YAxisTickContentProps) => <CategoryTick {...props} colors={c} />}
        label={{ value: yLabel, position: 'top', offset: 10, fill: c.textMuted, fontSize: 12 }}
      />
      {reference && (
        <ReferenceLine
          x={reference.value}
          stroke={c.text}
          strokeDasharray="4 4"
          label={{ value: reference.label, position: 'top', fill: c.text, fontSize: 12 }}
        />
      )}
      <Tooltip
        cursor={{ fill: c.grid }}
        content={(props) => <ChartTooltip {...props} unit={` ${unit}`} />}
      />
      <Bar
        isAnimationActive={!reduceMotion}
        dataKey="insecure"
        name="Insecure"
        fill={c.insecure}
        barSize={12}
        radius={[0, 4, 4, 0]}
      >
        <LabelList dataKey="insecure" content={valueLabel} />
      </Bar>
      <Bar
        isAnimationActive={!reduceMotion}
        dataKey="hardened"
        name="Hardened"
        fill={c.hardened}
        barSize={12}
        radius={[0, 4, 4, 0]}
      >
        <LabelList dataKey="hardened" content={valueLabel} />
      </Bar>
    </BarChart>
  )
}
