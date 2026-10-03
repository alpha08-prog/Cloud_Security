import type { ReactNode } from 'react'
import './SectionFrame.css'

interface SectionFrameProps {
  title: string
  summary: string
  /** Where the section's content comes from — figures, tables, or other. */
  source: string
  /** Optional caveat shown as a highlighted chip (e.g. "Conceptual model"). */
  badge?: string
  children: ReactNode
}

/** Common heading + source citation wrapped around every section. */
export function SectionFrame({ title, summary, source, badge, children }: SectionFrameProps) {
  return (
    <article className="section">
      <header className="section__header">
        <h2 className="section__title">{title}</h2>
        <p className="section__summary">{summary}</p>
        <div className="section__meta">
          <span className="chip">
            <span className="chip__key">Source</span> {source}
          </span>
          {badge && <span className="chip chip--highlight">{badge}</span>}
        </div>
      </header>
      {children}
    </article>
  )
}

/** Stand-in body for sections that haven't been built yet. */
export function Placeholder() {
  return (
    <div className="placeholder">
      <p className="placeholder__title">Not built yet</p>
      <p className="placeholder__body">This section is scaffolded and waiting for content.</p>
    </div>
  )
}
