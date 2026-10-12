import { SegmentedControl } from '../../components/SegmentedControl'
import { StatTile } from '../../components/charts/StatTile'
import { StatusBadge } from '../../components/StatusBadge'
import { AUDITS, E1, E2, E3, MANIFEST } from '../../data/results'
import { useChartColors } from '../../hooks/useChartColors'
import { useSubview } from '../../hooks/useSubview'
import { e1Summary, e2Summary, e3Summary, ms, pct } from '../../lib/evidence'
import { AuditView } from './AuditView'
import { DetectionView } from './DetectionView'
import { HypothesesView } from './HypothesesView'
import { NoisyView } from './NoisyView'
import { SegmentationView } from './SegmentationView'
import './Results.css'

const VIEWS = ['audit', 'noisy', 'segmentation', 'detection', 'hypotheses'] as const
type View = (typeof VIEWS)[number]

const VIEW_OPTIONS: { value: View; label: React.ReactNode }[] = [
  { value: 'audit', label: 'Audit' },
  { value: 'noisy', label: <>Noisy neighbour <span className="segmented__hint">· E1</span></> },
  { value: 'segmentation', label: <>Segmentation <span className="segmented__hint">· E2</span></> },
  { value: 'detection', label: <>Detection <span className="segmented__hint">· E3</span></> },
  { value: 'hypotheses', label: 'Hypotheses' },
]

const factor = (v: number | null | undefined) => (v === null || v === undefined ? '–' : `×${v.toFixed(1)}`)

export function Results() {
  const c = useChartColors()
  const [view, setView] = useSubview<View>('results', VIEWS, 'audit')
  const h = AUDITS.hardened
  const i = AUDITS.insecure
  const hypotheses = [...E1.hypotheses, ...E2.hypotheses, ...E3.hypotheses].length

  return (
    <div className="results">
      <div className="results__tiles">
        <StatTile
          label="Policy gate"
          swatch={c.hardened}
          value={<StatusBadge status={h.gate.passed ? 'pass' : 'fail'} label={h.gate.passed ? 'Passes' : 'Fails'} />}
          note={
            <>
              insecure: {i.gate.blocking.length} blocking failures
              {h.gate.waived.length > 0 && ` · ${h.gate.waived.length} waived host issues`}
            </>
          }
        />
        <StatTile
          label="Isolation coverage"
          swatch={c.hardened}
          value={pct(h.scores.overall.score)}
          note={`insecure: ${pct(i.scores.overall.score)} · 30 weighted checks`}
        />
        <StatTile
          label="Isolation paths open (E2)"
          swatch={c.hardened}
          value={`${e2Summary('hardened')?.openPaths ?? '–'} / ${e2Summary('hardened')?.probes ?? '–'}`}
          note={`insecure: ${e2Summary('insecure')?.openPaths ?? '–'} / ${e2Summary('insecure')?.probes ?? '–'}`}
        />
        <StatTile
          label="p99 slowdown from a noisy neighbour (E1)"
          swatch={c.hardened}
          value={factor(e1Summary('hardened')?.interferenceFactor)}
          note={`insecure: ${factor(e1Summary('insecure')?.interferenceFactor)}`}
        />
        <StatTile
          label="Isolation-breaking actions detected (E3)"
          swatch={c.hardened}
          value={`${e3Summary('hardened')?.detected ?? '–'} / ${e3Summary('hardened')?.expected ?? '–'}`}
          note={`median ${ms(e3Summary('hardened')?.medianLatencyMs)} · ${e3Summary('hardened')?.falsePositives ?? '–'} false positives`}
        />
      </div>

      <div className="toolbar">
        <SegmentedControl label="Results view" options={VIEW_OPTIONS} value={view} onChange={setView} />
        {E1.variant === 'ci' && (
          <span className="badge badge--highlight" title="Short measurement windows; numbers are indicative">
            Smoke-run data
          </span>
        )}
      </div>

      {view === 'audit' && <AuditView />}
      {view === 'noisy' && <NoisyView />}
      {view === 'segmentation' && <SegmentationView />}
      {view === 'detection' && <DetectionView />}
      {view === 'hypotheses' && <HypothesesView />}

      <footer className="results__provenance">
        <strong>Provenance.</strong> Published {new Date(MANIFEST.generatedAt).toLocaleString()} from commit{' '}
        <code>{MANIFEST.gitSha}</code> on <code>{MANIFEST.platform}</code>: Docker{' '}
        {h.environment.dockerServerVersion}, kernel {h.environment.kernelVersion},{' '}
        {h.environment.logicalCpus} logical CPUs ({h.environment.physicalCores} cores), cgroup v
        {h.environment.cgroupVersion}. Experiment variant: {E1.variant === 'full' ? 'full' : 'CI smoke'}.{' '}
        {hypotheses} pre-registered hypotheses in{' '}
        <a href="https://github.com/alpha08-prog/Cloud_Security/blob/main/docs/experiments.md">
          docs/experiments.md
        </a>
        .
      </footer>
    </div>
  )
}
