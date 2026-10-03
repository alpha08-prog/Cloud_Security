import type { ReactNode } from 'react'
import { cx } from '../../lib/format'

interface StatTileProps {
  label: string
  value: ReactNode
  note?: ReactNode
  /** Series swatch shown before the label, tying the tile to a chart series. */
  swatch?: string
  highlight?: boolean
}

export function StatTile({ label, value, note, swatch, highlight }: StatTileProps) {
  return (
    <div className={cx('card stat-tile', highlight && 'stat-tile--highlight')}>
      <p className="stat-tile__label">
        {swatch && (
          <span className="stat-tile__key" style={{ background: swatch }} aria-hidden="true" />
        )}
        {label}
      </p>
      <p className="stat-tile__value">{value}</p>
      {note && <p className="stat-tile__note">{note}</p>}
    </div>
  )
}
