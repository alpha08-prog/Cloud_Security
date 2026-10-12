import { ChartCard, DataTable, SeriesLegend, type Column } from '../../components/charts/ChartCard'
import { ProfileBarChart, type ProfileRow } from '../../components/charts/ProfileBarChart'
import { StatusBadge } from '../../components/StatusBadge'
import type { E1Run, ProfileName } from '../../data/resultTypes'
import { E1, E3, PROFILE_LABEL } from '../../data/results'
import { useChartColors } from '../../hooks/useChartColors'
import { e1Summary, ms } from '../../lib/evidence'

const median = (xs: number[]) => {
  if (!xs.length) return null
  const s = [...xs].sort((a, b) => a - b)
  const m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}

const stat = (p: ProfileName, arm: E1Run['arm'], q: 'med' | 'p99') =>
  median(E1.runs.filter((r) => r.valid && r.profile === p && r.arm === arm).map((r) => r.latencyMs[q]))

const ROWS: ProfileRow[] = [
  { key: 'b50', label: 'Median, alone', insecure: stat('insecure', 'baseline', 'med'), hardened: stat('hardened', 'baseline', 'med') },
  { key: 'n50', label: 'Median, noisy', insecure: stat('insecure', 'noisy', 'med'), hardened: stat('hardened', 'noisy', 'med') },
  { key: 'b99', label: 'p99, alone', insecure: stat('insecure', 'baseline', 'p99'), hardened: stat('hardened', 'baseline', 'p99') },
  { key: 'n99', label: 'p99, noisy', insecure: stat('insecure', 'noisy', 'p99'), hardened: stat('hardened', 'noisy', 'p99') },
]

const top = Math.max(E1.config.sloP99Ms, ...ROWS.flatMap((r) => [r.insecure ?? 0, r.hardened ?? 0]))
const STEP = top > 60 ? 20 : top > 30 ? 10 : 5
const MAX = Math.ceil((top * 1.1) / STEP) * STEP
const TICKS = Array.from({ length: MAX / STEP + 1 }, (_, i) => i * STEP)

const RUN_COLUMNS: readonly Column<E1Run>[] = [
  { header: 'Profile', cell: (r) => PROFILE_LABEL[r.profile] },
  { header: 'Arm', cell: (r) => (r.arm === 'noisy' ? 'noisy neighbour' : 'alone') },
  { header: 'Rep', cell: (r) => r.repetition, numeric: true },
  { header: 'p50 ms', cell: (r) => r.latencyMs.med.toFixed(1), numeric: true },
  { header: 'p99 ms', cell: (r) => r.latencyMs.p99.toFixed(1), numeric: true },
  { header: 'max ms', cell: (r) => r.latencyMs.max.toFixed(1), numeric: true },
  { header: 'Tenant B cores', cell: (r) => r.noisyCoresUsed?.toFixed(2) ?? '–', numeric: true },
  { header: 'Victim CPU wait %', cell: (r) => r.victimCpuPressurePct?.toFixed(2) ?? '–', numeric: true },
  { header: 'Valid', cell: (r) => <StatusBadge status={r.valid ? 'pass' : 'fail'} label={r.valid ? 'yes' : r.invalidReason ?? 'no'} /> },
]

export function NoisyView() {
  const c = useChartColors()
  const det = E3.results.find((r) => r.profile === 'insecure' && r.triggerId === 'T7')
  const quiet = E3.results.find((r) => r.profile === 'hardened' && r.triggerId === 'T7')

  return (
    <div className="results__view">
      <p className="results__lede">
        Tenant A serves {E1.config.ratePerSecond} requests/s (an open-model load, so a slow server cannot slow the
        load generator down). Then tenant B starts a CPU-burning job sized to every core on the host. Does A’s
        latency hold? The load generator has its own physical core in both profiles, so it is never the thing
        being starved.
      </p>

      <div className="data-grid">
        <ChartCard
          title="Tenant A latency, alone vs with a noisy neighbour"
          subtitle={`Median over valid runs. Dashed line: the ${E1.config.sloP99Ms} ms p99 SLO.`}
          legend={
            <SeriesLegend
              items={[
                { label: 'Insecure', color: c.insecure },
                { label: 'Hardened', color: c.hardened },
              ]}
            />
          }
          caption={
            <>
              <strong>Source:</strong> experiment E1, {E1.config.warmupSeconds} s warm-up + {E1.config.measureSeconds} s
              measured × {E1.config.repetitions} repetition{E1.config.repetitions > 1 ? 's' : ''}, arms interleaved.
            </>
          }
          table={<DataTable rows={E1.runs} columns={RUN_COLUMNS} rowKey={(r) => `${r.profile}-${r.arm}-${r.repetition}`} />}
        >
          <ProfileBarChart
            rows={ROWS}
            max={MAX}
            ticks={TICKS}
            unit="ms"
            xLabel="Latency (ms)"
            yLabel="Tenant A"
            reference={{ value: E1.config.sloP99Ms, label: 'SLO' }}
            labelWidth={112}
          />
        </ChartCard>

        <div className="results__side">
          {(['insecure', 'hardened'] as const).map((p) => {
            const s = e1Summary(p)
            return (
              <div key={p} className="card results__factor">
                <p className="eyebrow">
                  <span className="results__key" style={{ background: p === 'insecure' ? c.insecure : c.hardened }} />
                  {PROFILE_LABEL[p]}
                </p>
                <p className="results__factor-value">
                  ×{s?.interferenceFactor?.toFixed(1) ?? '–'}
                </p>
                <p className="results__factor-note">
                  p99 {s?.baselineP99Ms?.toFixed(1)} → {s?.noisyP99Ms?.toFixed(1)} ms under noise
                </p>
              </div>
            )
          })}
          <div className="callout">
            <p>
              <strong>Why.</strong> In the insecure profile B’s job runs on every core, so A’s requests queue
              behind it. Hardened, B is confined to its own cores and CPU quota (it is throttled instead), so A
              never notices.
            </p>
            <p>
              <strong>Detected, too.</strong> The auditor flagged the noisy neighbour (DET-08) in{' '}
              {ms(det?.latencyMs)} in the insecure profile, and stayed {quiet?.detected ? 'NOT silent' : 'silent'} when
              hardened (experiment E3, trigger T7).
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
