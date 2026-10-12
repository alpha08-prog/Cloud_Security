import { HostDiagram } from '../../components/HostDiagram'
import { ChartCard, SeriesLegend } from '../../components/charts/ChartCard'
import { GapChart } from '../../components/charts/GapChart'
import { PairedRadarChart } from '../../components/charts/PairedRadarChart'
import { REQUIREMENTS } from '../../data/requirements'
import { VIRTUALIZATION_RADAR_MAX, getShare } from '../../data/stats'
import { UNDER_SOLVED } from '../../data/taxonomy'
import { useChartColors } from '../../hooks/useChartColors'
import { CATEGORY_ROWS_BY_GAP, VIRTUALIZATION_ROWS } from '../../lib/chartRows'
import { formatGap } from '../../lib/format'
import { QuoteWithRequirements } from '../requirements/Quote'
import './Gap.css'

const gap = getShare(UNDER_SOLVED)
const ratio = Math.round(gap.concern / gap.solution)

export function Gap() {
  const c = useChartColors()
  return (
    <div className="gap">
      <div className="gap__hero card">
        <div>
          <p className="eyebrow">Virtualization: solutions minus concerns</p>
          <p className="gap__number">{formatGap(gap.gap)}</p>
          <p className="gap__sub">
            {gap.concern}% of concern citations · {gap.solution}% of solution citations
          </p>
        </div>
        <div className="gap__thesis">
          <p>
            Gonzalez et al. counted, across 200+ references, how often each cloud-security concern is{' '}
            <strong>raised</strong> and how often a <strong>solution</strong> is proposed. Legal,
            compliance and governance concerns are matched by solutions. Virtualization is the
            exception: it draws {ratio}× as large a share of concerns as of solutions.
          </p>
          <p>
            The paper’s conclusion is a brief for future work, not just a statistic, and this project
            takes it literally: <a href="#requirements">four requirements</a>, a{' '}
            <a href="#system">system that implements them</a>, and{' '}
            <a href="#results">measurements</a> that test it.
          </p>
        </div>
      </div>

      <div className="gap__charts">
        <ChartCard
          title="Where solutions fall short"
          subtitle="Solution share minus concern share per category, in percentage points."
          caption={
            <>
              <strong>Source:</strong> computed from Gonzalez et al. (2012), Figures 6 &amp; 8 (exact).
            </>
          }
        >
          <GapChart rows={CATEGORY_ROWS_BY_GAP} bound={12} xLabel="Gap in pts (solution − concern)" yLabel="Category" />
        </ChartCard>

        <ChartCard
          title="Inside virtualization (Figure 11)"
          subtitle="Citations per sub-issue. Isolation and cross-VM attacks have almost no solutions."
          legend={
            <SeriesLegend
              items={[
                { label: 'Concern', color: c.concern, shape: 'line' },
                { label: 'Solution', color: c.solution, shape: 'line' },
              ]}
            />
          }
          caption={
            <>
              <strong>Source:</strong> Gonzalez et al. (2012), Figure 11. <strong>Approximate</strong>: values
              measured from the figure, scale 0–{VIRTUALIZATION_RADAR_MAX}.
            </>
          }
        >
          <PairedRadarChart rows={VIRTUALIZATION_ROWS} max={VIRTUALIZATION_RADAR_MAX} tickCount={6} unit="" />
        </ChartCard>
      </div>

      <section className="card gap__brief" aria-labelledby="brief-heading">
        <p className="eyebrow">The paper’s brief · p.16</p>
        <h3 id="brief-heading">What a solution should do</h3>
        <QuoteWithRequirements />
        <ol className="gap__reqs">
          {REQUIREMENTS.map((r) => (
            <li key={r.id}>
              <span className="badge badge--accent">{r.id}</span> <strong>{r.short}</strong>{' '}
              <span className="gap__req-phrase">“{r.phrase}”</span>
            </li>
          ))}
        </ol>
        <a className="link-cta" href="#requirements">
          How IsoLab implements and verifies each one →
        </a>
      </section>

      <details className="card gap__why">
        <summary>Why tenants sharing one host is a security problem</summary>
        <div className="gap__why-body">
          <p>
            Cloud tenants run side by side on the same physical machine. The hypervisor (or, for
            containers, the shared kernel and engine) separates them logically, but they still share
            CPU cores, caches and memory. If that separation is misconfigured or imperfect, one tenant
            can read, slow down or interfere with another: the isolation, data-leakage and cross-VM
            concerns of Figure 11.
          </p>
          <HostDiagram />
          <p className="figure-caption">
            Conceptual diagram. IsoLab audits and enforces the separation and watches the shared
            hardware; it does not simulate attacks.
          </p>
        </div>
      </details>
    </div>
  )
}
