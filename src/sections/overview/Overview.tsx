import { ChartCard } from '../../components/charts/ChartCard'
import { GapChart } from '../../components/charts/GapChart'
import { getShare } from '../../data/stats'
import { DIMENSIONS, UNDER_SOLVED, getCategory } from '../../data/taxonomy'
import { CATEGORY_ROWS_BY_GAP } from '../../lib/chartRows'
import { cx, formatGap } from '../../lib/format'
import './Overview.css'

const gap = getShare(UNDER_SOLVED)
const ratio = Math.round(gap.concern / gap.solution)

// Each series sums to 100 across the seven categories, so a dimension's share
// is the sum of its categories' shares.
const DIMENSION_SHARES = DIMENSIONS.map((d) => {
  const concern = d.categories.reduce((sum, c) => sum + getShare(c).concern, 0)
  const solution = d.categories.reduce((sum, c) => sum + getShare(c).solution, 0)
  return { ...d, concern, solution, gap: solution - concern }
})

const NEXT = [
  { href: '#taxonomy', title: 'Taxonomy', body: 'Walk the four taxonomy trees (Figures 1–4).' },
  { href: '#data', title: 'Data', body: 'Every concern-vs-solution figure, charted (Figures 5–8, 11).' },
  { href: '#defenses', title: 'Defenses', body: 'Concrete controls for each concern category.' },
  { href: '#frameworks', title: 'Frameworks', body: 'CSA, ENISA and NIST guidance (Tables 1 & 2).' },
]

export function Overview() {
  return (
    <div className="overview">
      <div className="overview__hero card">
        <div className="overview__figure">
          <p className="eyebrow">Virtualization coverage gap</p>
          <p className="overview__number">{formatGap(gap.gap)}</p>
          <p className="overview__sub">
            {gap.concern}% of concern citations · {gap.solution}% of solution citations
          </p>
        </div>
        <div className="overview__thesis">
          <p>
            The paper surveys 200+ references and counts, for each cloud-security concern, how
            often it is <strong>raised</strong> versus how often a <strong>solution</strong> is
            proposed.
          </p>
          <p>
            Institutional concerns — legal issues, compliance, governance — are broadly matched by
            solutions. {getCategory(UNDER_SOLVED).label} is the one large deficit: its share of concern
            citations is {ratio}× its share of solution citations. Cross-VM and side-channel attacks
            sit inside that gap.
          </p>
        </div>
      </div>

      <div className="overview__dimensions">
        {DIMENSION_SHARES.map((d) => (
          <article key={d.id} className={cx('card overview__dimension', d.gap < 0 && 'is-deficit')}>
            <p className="eyebrow">Dimension · Figure {d.figure}</p>
            <h3>{d.label}</h3>
            <p className="overview__categories">
              {d.categories.map((c) => getCategory(c).label).join(' · ')}
            </p>
            <dl className="facts">
              <dt>Concern</dt>
              <dd className="num">{d.concern}%</dd>
              <dt>Solution</dt>
              <dd className="num">{d.solution}%</dd>
              <dt>Gap</dt>
              <dd className="num">{formatGap(d.gap)}</dd>
            </dl>
          </article>
        ))}
      </div>

      <ChartCard
        title="Where solutions fall short"
        subtitle="Solution share minus concern share for each category, in percentage points."
        caption={
          <>
            <strong>Source:</strong> computed from Gonzalez et al. (2012), Figures 6 &amp; 8. The
            dimension totals above are sums of these category shares.
          </>
        }
      >
        <GapChart
          rows={CATEGORY_ROWS_BY_GAP}
          bound={12}
          xLabel="Gap in pts (solution − concern)"
          yLabel="Category"
        />
      </ChartCard>

      <nav className="overview__next" aria-label="Explore the sections">
        {NEXT.map((n) => (
          <a key={n.href} className="card overview__link" href={n.href}>
            <span className="overview__link-title">{n.title} →</span>
            <span className="overview__link-body">{n.body}</span>
          </a>
        ))}
      </nav>
    </div>
  )
}
