import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts'
import { useChartColors } from '../../hooks/useChartColors'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import type { CveRow } from '../../lib/replicationRows'

interface RateMultiplesProps {
  rows: readonly CveRow[]
  panels: readonly { key: string; label: string }[]
  /** Shared upper bound so the panels compare at a glance. */
  max: number
  color: string
}

/**
 * Small multiples of one rate over time, one panel per series, on a shared y-scale.
 * Faceting keeps a single hue (no four-colour legend), and the partial last year is
 * drawn as a hollow point.
 */
export function RateMultiples({ rows, panels, max, color }: RateMultiplesProps) {
  const c = useChartColors()
  const reduceMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  return (
    <div className="rate-multiples">
      {panels.map((p) => (
        <figure key={p.key} className="rate-multiples__panel">
          <figcaption className="rate-multiples__title">{p.label}</figcaption>
          <LineChart
            data={rows as CveRow[]}
            responsive
            style={{ width: '100%', height: 150 }}
            margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
          >
            <CartesianGrid vertical={false} stroke={c.grid} />
            <XAxis
              dataKey="year"
              stroke={c.axis}
              tickLine={false}
              ticks={[rows[0]?.year, 2014, 2020, rows[rows.length - 1]?.year].filter(Boolean) as number[]}
              tick={{ fill: c.textMuted, fontSize: 11 }}
            />
            <YAxis
              domain={[0, max]}
              tickCount={3}
              stroke={c.axis}
              tickLine={false}
              axisLine={false}
              width={32}
              tick={{ fill: c.textMuted, fontSize: 11 }}
            />
            <Tooltip
              cursor={{ stroke: c.axis }}
              content={({ active, payload }) => {
                const row = payload?.[0]?.payload as CveRow | undefined
                if (!active || !row) return null
                const v = row[p.key]
                return (
                  <div className="chart-tooltip">
                    <p className="chart-tooltip__title">
                      {row.year}
                      {row.partial ? ' (partial year)' : ''}
                    </p>
                    <p style={{ margin: 0 }}>
                      <strong className="num">{typeof v === 'number' ? v.toFixed(1) : '–'}</strong>{' '}
                      <span style={{ color: 'var(--text-muted)' }}>per 10,000 CVEs · {p.label}</span>
                    </p>
                    <div className="chart-tooltip__footer">{row.total.toLocaleString()} CVEs published that year</div>
                  </div>
                )
              }}
            />
            <Line
              type="linear"
              dataKey={p.key}
              name={p.label}
              stroke={color}
              strokeWidth={2}
              isAnimationActive={!reduceMotion}
              dot={(props: { cx?: number; cy?: number; payload?: CveRow; index?: number }) => (
                <circle
                  key={props.index}
                  cx={props.cx}
                  cy={props.cy}
                  r={props.payload?.partial ? 4 : 0}
                  fill={c.surface}
                  stroke={color}
                  strokeWidth={2}
                />
              )}
              activeDot={{ r: 4, stroke: c.surface, strokeWidth: 2, fill: color }}
            />
          </LineChart>
        </figure>
      ))}
    </div>
  )
}
