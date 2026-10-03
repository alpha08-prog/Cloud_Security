import type { ReactNode } from 'react'
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  Tooltip,
} from 'recharts'
import { useChartColors } from '../../hooks/useChartColors'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import { ChartTooltip } from './ChartCard'

export interface RadarRow {
  key: string
  label: string
  concern: number
  solution: number
  highlight?: boolean
}

interface PairedRadarChartProps {
  rows: readonly RadarRow[]
  max: number
  /** Number of radius ticks including 0 (e.g. 4 → 0/10/20/30 for max 30). */
  tickCount?: number
  unit?: string
  height?: number
  tooltipFooter?: (label: string) => ReactNode
}

/** Split two-word labels onto two lines so the radar fits narrow screens. */
function wrapLabel(label: string): string[] {
  const space = label.indexOf(' ')
  return label.length > 10 && space > 0 ? [label.slice(0, space), label.slice(space + 1)] : [label]
}

/** Concern and solution outlines overlaid on one radar. */
export function PairedRadarChart({
  rows,
  max,
  tickCount = 4,
  unit = '%',
  height = 340,
  tooltipFooter,
}: PairedRadarChartProps) {
  const c = useChartColors()
  const narrow = useMediaQuery('(max-width: 480px)')
  const highlighted = new Set(rows.filter((r) => r.highlight).map((r) => r.label))
  const dot = (color: string) => ({ r: 4, fill: color, stroke: c.surface, strokeWidth: 2 })
  // Run the radius scale between the first two spokes so its ticks never sit on a label.
  const radiusAngle = 90 - 180 / rows.length

  return (
    <RadarChart
      data={rows as RadarRow[]}
      responsive
      style={{ width: '100%', height }}
      outerRadius={narrow ? '56%' : '66%'}
      margin={{ top: 12, right: 12, bottom: 12, left: 12 }}
    >
      <PolarGrid stroke={c.grid} />
      <PolarAngleAxis
        dataKey="label"
        tick={({ x, y, index, payload, textAnchor }) => {
          const label = String(payload.value)
          const strong = highlighted.has(label)
          const lines = wrapLabel(label)
          // Labels above the centre grow upward so they never cover the plot.
          // Spokes run clockwise from 12 o'clock.
          const above = Math.sin(((90 - (index * 360) / rows.length) * Math.PI) / 180) > 0.2
          return (
            <text
              x={x}
              y={y}
              textAnchor={textAnchor}
              fill={strong ? c.text : c.textMuted}
              fontSize={narrow ? 11 : 12}
              fontWeight={strong ? 650 : 400}
            >
              {lines.map((line, i) => (
                <tspan
                  key={line}
                  x={x}
                  dy={i === 0 ? (above ? 4 - (lines.length - 1) * 14 : 4) : 14}
                >
                  {line}
                </tspan>
              ))}
            </text>
          )
        }}
      />
      <PolarRadiusAxis
        angle={radiusAngle}
        domain={[0, max]}
        tickCount={tickCount}
        axisLine={false}
        // A surface-coloured halo keeps tick labels legible over the fills.
        tick={{ fill: c.textMuted, fontSize: 11, stroke: c.surface, strokeWidth: 3, paintOrder: 'stroke' }}
        tickFormatter={(v: number) => (v === 0 ? '' : `${v}${unit}`)}
      />
      <Tooltip content={(props) => <ChartTooltip {...props} unit={unit} footer={tooltipFooter} />} />
      <Radar
        name="Concern"
        dataKey="concern"
        stroke={c.concern}
        strokeWidth={2}
        fill={c.concern}
        fillOpacity={0.1}
        dot={dot(c.concern)}
      />
      <Radar
        name="Solution"
        dataKey="solution"
        stroke={c.solution}
        strokeWidth={2}
        fill={c.solution}
        fillOpacity={0.1}
        dot={dot(c.solution)}
      />
    </RadarChart>
  )
}
