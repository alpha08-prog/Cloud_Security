import type { Status } from '../data/resultTypes'
import './StatusBadge.css'

type Kind = Status | 'open' | 'blocked' | 'control'

const META: Record<Kind, { icon: string; label: string; tone: 'pass' | 'warn' | 'fail' | 'skip' }> = {
  pass: { icon: '✓', label: 'Pass', tone: 'pass' },
  warn: { icon: '!', label: 'Warn', tone: 'warn' },
  fail: { icon: '✕', label: 'Fail', tone: 'fail' },
  error: { icon: '✕', label: 'Error', tone: 'fail' },
  skip: { icon: '–', label: 'Skip', tone: 'skip' },
  open: { icon: '✕', label: 'Open', tone: 'fail' },
  blocked: { icon: '✓', label: 'Blocked', tone: 'pass' },
  control: { icon: '✓', label: 'Reachable', tone: 'pass' },
}

/** A state shown as icon + label, never colour alone. Text stays in text ink. */
export function StatusBadge({ status, label, note }: { status: Kind; label?: string; note?: string }) {
  const m = META[status]
  return (
    <span className={`status status--${m.tone}`}>
      <span className="status__icon" aria-hidden="true">
        {m.icon}
      </span>
      {label ?? m.label}
      {note && <span className="status__note">{note}</span>}
    </span>
  )
}
