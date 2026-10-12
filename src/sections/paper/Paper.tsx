import { SegmentedControl } from '../../components/SegmentedControl'
import { useSubview } from '../../hooks/useSubview'
import { DataDashboard } from '../data/DataDashboard'
import { Defenses } from '../defenses/Defenses'
import { Frameworks } from '../frameworks/Frameworks'
import { Taxonomy } from '../taxonomy/Taxonomy'

const VIEWS = ['figures', 'taxonomy', 'frameworks', 'controls'] as const
type View = (typeof VIEWS)[number]

const OPTIONS: { value: View; label: React.ReactNode }[] = [
  { value: 'figures', label: <>Figures <span className="segmented__hint">· 5–8, 11</span></> },
  { value: 'taxonomy', label: <>Taxonomy <span className="segmented__hint">· 1–4</span></> },
  { value: 'frameworks', label: <>Frameworks <span className="segmented__hint">· Tables 1–2</span></> },
  { value: 'controls', label: 'Controls by category' },
]

/** Appendix: the paper itself, explorable. */
export function Paper() {
  const [view, setView] = useSubview<View>('paper', VIEWS, 'figures')
  return (
    <div className="paper">
      <div className="toolbar">
        <SegmentedControl label="Paper view" options={OPTIONS} value={view} onChange={setView} />
      </div>
      {view === 'figures' && <DataDashboard />}
      {view === 'taxonomy' && <Taxonomy />}
      {view === 'frameworks' && <Frameworks />}
      {view === 'controls' && <Defenses />}
    </div>
  )
}
