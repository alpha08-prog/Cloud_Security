import type { ReactNode } from 'react'
import type { TooltipContentProps } from 'recharts'
import { cx } from '../../lib/format'
import './charts.css'

interface ChartCardProps {
  title: string
  subtitle?: ReactNode
  legend?: ReactNode
  /** Source line under the plot, citing the figure. */
  caption: ReactNode
  /** Accessible table twin of the chart, shown on demand. */
  table?: ReactNode
  className?: string
  children: ReactNode
}

export function ChartCard({
  title,
  subtitle,
  legend,
  caption,
  table,
  className,
  children,
}: ChartCardProps) {
  return (
    <figure className={cx('card chart-card', className)}>
      <div className="chart-card__head">
        <h3 className="card__title">{title}</h3>
        {subtitle && <p className="card__subtitle">{subtitle}</p>}
      </div>
      {legend}
      <div className="chart-card__plot">{children}</div>
      <figcaption className="figure-caption chart-card__caption">{caption}</figcaption>
      {table && (
        <details className="table-view">
          <summary>View as table</summary>
          {table}
        </details>
      )}
    </figure>
  )
}

export interface LegendItem {
  label: string
  color: string
  /** Mirror the mark: rect for bars, line for lines/radar outlines. */
  shape?: 'rect' | 'line'
}

export function SeriesLegend({ items }: { items: readonly LegendItem[] }) {
  return (
    <ul className="series-legend">
      {items.map((item) => (
        <li key={item.label}>
          <span
            className={cx('series-legend__key', item.shape === 'line' && 'series-legend__key--line')}
            style={{ background: item.color }}
            aria-hidden="true"
          />
          {item.label}
        </li>
      ))}
    </ul>
  )
}

interface ChartTooltipProps extends Partial<TooltipContentProps> {
  unit?: string
  /** Extra line under the values, e.g. a gap or a note. */
  footer?: (label: string) => ReactNode
}

/** Values lead, series names follow; series keyed with a short line in its color. */
export function ChartTooltip({ active, payload, label, unit = '', footer }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  const title = String(label ?? payload[0]?.payload?.label ?? '')
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip__title">{title}</p>
      <ul>
        {payload.map((entry) => (
          <li key={String(entry.dataKey ?? entry.name)}>
            <span
              className="chart-tooltip__key"
              style={{ background: entry.color ?? entry.stroke }}
              aria-hidden="true"
            />
            <strong className="num">
              {String(entry.value)}
              {unit}
            </strong>
            <span>{entry.name}</span>
          </li>
        ))}
      </ul>
      {footer && <div className="chart-tooltip__footer">{footer(title)}</div>}
    </div>
  )
}

export interface Column<Row> {
  header: string
  cell: (row: Row) => ReactNode
  numeric?: boolean
}

export function DataTable<Row>({
  rows,
  columns,
  rowKey,
}: {
  rows: readonly Row[]
  columns: readonly Column<Row>[]
  rowKey: (row: Row) => string
}) {
  return (
    <div className="data-table__wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.header} className={c.numeric ? 'is-num' : undefined} scope="col">
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c) => (
                <td key={c.header} className={c.numeric ? 'is-num num' : undefined}>
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
