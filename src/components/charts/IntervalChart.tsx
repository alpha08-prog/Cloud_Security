import {
  CartesianGrid,
  ErrorBar,
  ReferenceLine,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useChartColors } from '../../hooks/useChartColors'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import type { IntervalRow } from '../../lib/replicationRows'

export interface IntervalSeries {
  key: string
  label: string
  color: string
  /** Hollow marker, e.g. for a reference value read from a chart. */
  hollow?: boolean
}

interface IntervalChartProps {
  rows: readonly IntervalRow[]
  series: readonly IntervalSeries[]
  domain: [number, number]
  ticks?: number[]
  yLabel: string
  references?: readonly { y: number; label: string }[]
  format?: (v: number) => string
  height?: number
}

interface Point {
  x: number
  y: number
  err: [number, number]
  row: string
  series: string
  ci: [number, number] | null
}

/**
 * Point estimates with 95% interval whiskers, one column per row and one marker per
 * series (offset side by side). Reference lines mark thresholds such as 0 or the 2012 value.
 */
export function IntervalChart({
  rows,
  series,
  domain,
  ticks,
  yLabel,
  references = [],
  format = (v) => v.toFixed(1),
  height = 300,
}: IntervalChartProps) {
  const c = useChartColors()
  const reduceMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const narrow = useMediaQuery('(max-width: 560px)')
  const spread = series.length > 1 ? 0.18 : 0

  const points = (s: IntervalSeries, k: number): Point[] =>
    rows.flatMap((r, i) => {
      const v = r.values[s.key]
      if (!v || v.value === null) return []
      const offset = series.length > 1 ? (k - (series.length - 1) / 2) * spread * 2 : 0
      const err: [number, number] = v.ci ? [v.value - v.ci[0], v.ci[1] - v.value] : [0, 0]
      return [{ x: i + offset, y: v.value, err, row: r.label, series: s.label, ci: v.ci }]
    })

  return (
    <ScatterChart
      responsive
      style={{ width: '100%', height }}
      margin={{ top: 16, right: 20, bottom: 8, left: narrow ? 12 : 4 }}
    >
      <CartesianGrid vertical={false} stroke={c.grid} />
      <XAxis
        type="number"
        dataKey="x"
        domain={[-0.6, rows.length - 0.4]}
        ticks={rows.map((_, i) => i)}
        tickFormatter={(i: number) => (narrow ? rows[i]?.short : undefined) ?? rows[i]?.label ?? ''}
        interval={0}
        stroke={c.axis}
        tickLine={false}
        tick={{ fill: c.textMuted, fontSize: narrow ? 11 : 12 }}
        angle={narrow ? -30 : 0}
        textAnchor={narrow ? 'end' : 'middle'}
        height={narrow ? 46 : 30}
      />
      <YAxis
        type="number"
        dataKey="y"
        domain={domain}
        ticks={ticks}
        tickFormatter={format}
        stroke={c.axis}
        tickLine={false}
        axisLine={false}
        width={58}
        tick={{ fill: c.textMuted, fontSize: 12 }}
        label={{ value: yLabel, angle: -90, position: 'insideLeft', offset: 0, fill: c.textMuted, fontSize: 12 }}
      />
      {references.map((r) => (
        <ReferenceLine
          key={r.label}
          y={r.y}
          stroke={c.axis}
          strokeDasharray={r.y === 0 ? undefined : '4 4'}
          label={{ value: r.label, position: 'insideTopRight', fill: c.textMuted, fontSize: 11 }}
        />
      ))}
      <Tooltip
        cursor={false}
        content={({ active, payload }) => {
          const p = payload?.[0]?.payload as Point | undefined
          if (!active || !p) return null
          return (
            <div className="chart-tooltip">
              <p className="chart-tooltip__title">{p.row}</p>
              <p style={{ margin: 0 }}>
                <strong className="num">{format(p.y)}</strong>{' '}
                <span style={{ color: 'var(--text-muted)' }}>{p.series}</span>
              </p>
              <div className="chart-tooltip__footer">
                {p.ci ? `95% CI ${format(p.ci[0])} to ${format(p.ci[1])}` : 'No interval (reference value)'}
              </div>
            </div>
          )
        }}
      />
      {series.map((s, k) => (
        <Scatter
          key={s.key}
          name={s.label}
          data={points(s, k)}
          isAnimationActive={!reduceMotion}
          shape={(props: { cx?: number; cy?: number }) => (
            <circle
              cx={props.cx}
              cy={props.cy}
              r={5.5}
              fill={s.hollow ? c.surface : s.color}
              stroke={s.hollow ? s.color : c.surface}
              strokeWidth={2}
            />
          )}
        >
          <ErrorBar
            dataKey="err"
            direction="y"
            width={6}
            strokeWidth={2}
            stroke={s.color}
            isAnimationActive={!reduceMotion}
          />
        </Scatter>
      ))}
    </ScatterChart>
  )
}
