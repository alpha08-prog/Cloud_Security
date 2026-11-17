import { useState } from 'react'
import { SegmentedControl } from '../../components/SegmentedControl'
import { StatusBadge } from '../../components/StatusBadge'
import { ChartCard, DataTable, SeriesLegend } from '../../components/charts/ChartCard'
import { IntervalChart } from '../../components/charts/IntervalChart'
import { PairedBarChart } from '../../components/charts/PairedBarChart'
import { RateMultiples } from '../../components/charts/RateMultiples'
import { StatTile } from '../../components/charts/StatTile'
import {
  CVE_AXIS_LABEL,
  REPLICATION_HYPOTHESES,
  REPLICATION_STEPS,
  VALIDITY_CHECK_LABEL,
} from '../../data/replication'
import type { Interval, ReplicationResult, Verdict } from '../../data/resultTypes'
import { REPLICATION } from '../../data/results'
import { getCategory, type CategoryId } from '../../data/taxonomy'
import { useChartColors } from '../../hooks/useChartColors'
import { formatGap } from '../../lib/format'
import {
  axisRatioRows,
  categoryRows,
  cveRows,
  inScopeTotals,
  periodLabel,
  periods,
  robustnessRows,
  virtualizationGapRows,
} from '../../lib/replicationRows'

const BADGE: Record<Verdict, { status: 'pass' | 'fail' | 'skip'; label: string }> = {
  supported: { status: 'pass', label: 'Supported' },
  'not-supported': { status: 'fail', label: 'Not supported' },
  inconclusive: { status: 'skip', label: 'Inconclusive' },
}

const ci = (v: Interval | null | undefined, digits = 1) =>
  v ? `[${v[0].toFixed(digits)}, ${v[1].toFixed(digits)}]` : '–'
const num = (v: number | null | undefined, digits = 2) => (v === null || v === undefined ? '–' : v.toFixed(digits))
/** Signed points with one decimal and a true minus sign: "+0.4", "−2.0". */
const gapText = (v: number | null | undefined) =>
  v === null || v === undefined ? '–' : `${v >= 0.05 ? '+' : v <= -0.05 ? '−' : ''}${Math.abs(v).toFixed(1)}`

export function ReplicationView({ doc = REPLICATION }: { doc?: ReplicationResult | null }) {
  return doc ? <ReplicationResults doc={doc} /> : <ReplicationPending />
}

function ReplicationPending() {
  return (
    <div className="results__view">
      <p className="results__lede">
        Does the survey’s headline still hold? This study re-runs its own counting method, concern and solution
        entries per sub-category, on 7,290 cloud-security abstracts from 2013–2026, under a protocol written
        before any data was analysed (<code>docs/replication.md</code>). Results are published only after the
        classifier has been checked against blind human labels.
      </p>
      <section className="card results__block">
        <h3 className="card__title">Status</h3>
        <p>
          <StatusBadge status="skip" label="Pending" /> Snapshots fetched and hashed, classifier frozen, validation
          sample drawn. Waiting for the blind labels; then <code>lab.py rep analyze</code> and{' '}
          <code>rep publish</code> fill this view.
        </p>
      </section>
      <ol className="replication__steps">
        {REPLICATION_STEPS.map((s) => (
          <li key={s.title} className="card">
            <h3 className="card__title">{s.title}</h3>
            <p>{s.body}</p>
          </li>
        ))}
      </ol>
      <section className="card results__block">
        <h3 className="card__title">Pre-registered hypotheses</h3>
        <ul className="results__hypotheses">
          {REPLICATION_HYPOTHESES.map((h) => (
            <li key={h.id}>
              <StatusBadge status="skip" label={`${h.id} · Pending`} />
              <p>{h.statement}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function ReplicationResults({ doc }: { doc: ReplicationResult }) {
  const c = useChartColors()
  const eras = doc.protocol.eras
  const last = eras[eras.length - 1]
  const [period, setPeriod] = useState<string>(last.id)
  const totals = inScopeTotals(doc)
  const gapLast = doc.categories.find((r) => r.era === last.id && r.category === 'virtualization')
  const gate = doc.validation.weighted.validityGate
  const cve = cveRows(doc)
  const subAxes = ['isolation', 'cross-vm-attacks', 'data-leakage']
  const maxOf = (keys: string[]) =>
    Math.max(1, ...cve.flatMap((r) => keys.map((k) => (typeof r[k] === 'number' ? (r[k] as number) : 0))))
  const allPeriods = periods(doc)

  return (
    <div className="results__view">
      <p className="results__lede">
        The survey’s own method, applied to {totals.inScope.toLocaleString()} in-scope abstracts out of{' '}
        {totals.analysed.toLocaleString()} sampled from 2013–2026: every (abstract, sub-category) pair is a concern
        entry, and abstracts that propose something add solution entries. Same metric, same gap, with 95% intervals
        and pre-registered verdicts.
      </p>
      {doc.limitations[0]?.startsWith('SYNTHETIC') && (
        <p className="badge badge--highlight">Synthetic fixture: not a result</p>
      )}
      {!doc.validityGateMet && (
        <p className="replication__warning card">
          <StatusBadge status="warn" label="Validity gate not met" /> The classifier did not reach the
          pre-registered agreement with the blind labels; the shares below are reported, but read them as indicative.
        </p>
      )}

      <div className="results__tiles">
        <StatTile
          label={`Virtualization gap, ${last.label}`}
          swatch={c.highlight}
          value={gapText(gapLast?.gapPts)}
          note={`95% CI ${ci(gapLast?.gapCi)} · 2012: −9 pts`}
        />
        <StatTile
          label="Abstracts in scope"
          swatch={c.muted}
          value={totals.inScope.toLocaleString()}
          note={`of ${totals.analysed.toLocaleString()} analysed · 3 eras`}
        />
        <StatTile
          label="Validity gate (blind labels)"
          swatch={c.muted}
          value={<StatusBadge status={gate.met ? 'pass' : 'fail'} label={gate.met ? 'Met' : 'Not met'} />}
          note={`${doc.validation.n} labelled abstracts · ${doc.validation.repeats} hidden repeats`}
        />
      </div>

      <ChartCard
        title="Is virtualization still under-solved?"
        subtitle="Virtualization’s solution share minus its concern share, in percentage points, with 95% bootstrap intervals."
        caption={
          <>
            <strong>Source:</strong> 2012 from Gonzalez et al. (2012), Figures 6 &amp; 8 (exact); later periods
            recomputed with the same unit (<code>{doc.protocol.document}</code>). Below 0 means raised more often than
            solved.
          </>
        }
        table={
          <DataTable
            rows={virtualizationGapRows(doc)}
            rowKey={(r) => r.key}
            columns={[
              { header: 'Period', cell: (r) => r.label },
              { header: 'Gap (pts)', cell: (r) => gapText(r.values.gap.value), numeric: true },
              { header: '95% CI', cell: (r) => ci(r.values.gap.ci), numeric: true },
            ]}
          />
        }
      >
        <IntervalChart
          rows={virtualizationGapRows(doc)}
          series={[{ key: 'gap', label: 'Virtualization gap', color: c.highlight }]}
          domain={[-16, 8]}
          ticks={[-16, -12, -8, -4, 0, 4, 8]}
          yLabel="Gap (pts)"
          references={[
            { y: 0, label: '' },
            { y: -9, label: '2012: −9' },
          ]}
          format={(v) => (Number.isInteger(v) ? formatGap(v, '') : gapText(v))}
        />
      </ChartCard>

      <ChartCard
        title="Figures 6 & 8, recomputed"
        subtitle="Share of concern entries and of solution entries per category."
        legend={
          <div className="replication__legend-row">
            <SeriesLegend
              items={[
                { label: 'Concern share', color: c.concern },
                { label: 'Solution share', color: c.solution },
              ]}
            />
            <SegmentedControl
              label="Period"
              options={allPeriods.map((p) => ({ value: p, label: periodLabel(p) }))}
              value={period}
              onChange={setPeriod}
            />
          </div>
        }
        caption={
          <>
            <strong>Source:</strong> {period === '2012' ? 'Gonzalez et al. (2012), Figures 6 & 8.' : 'this replication.'}{' '}
            Unit: {doc.protocol.unit}.
          </>
        }
        table={
          <DataTable
            rows={doc.categories.filter((r) => r.era === period)}
            rowKey={(r) => r.category}
            columns={[
              { header: 'Category', cell: (r) => getCategory(r.category).label },
              { header: 'Concern %', cell: (r) => num(r.concernPct, 1), numeric: true },
              { header: 'Solution %', cell: (r) => num(r.solutionPct, 1), numeric: true },
              { header: 'Gap (pts)', cell: (r) => gapText(r.gapPts), numeric: true },
              { header: 'Gap 95% CI', cell: (r) => ci(r.gapCi), numeric: true },
              { header: 'Entries (c / s)', cell: (r) => (r.concernEntries === null ? '–' : `${r.concernEntries} / ${r.solutionEntries}`), numeric: true },
            ]}
          />
        }
      >
        <PairedBarChart rows={categoryRows(doc, period)} max={40} ticks={[0, 10, 20, 30, 40]} xLabel="Share of entries (%)" yLabel="Category" />
      </ChartCard>

      <ChartCard
        title="Figure 11’s question: which sub-issues get answered?"
        subtitle="Solution entries per concern entry for each virtualization sub-issue."
        legend={
          <SeriesLegend
            items={[
              { label: '2012 survey (read from Figure 11)', color: c.muted },
              { label: '2013–26 pooled, 95% CI', color: c.highlight },
            ]}
          />
        }
        caption={
          <>
            <strong>Source:</strong> Gonzalez et al. (2012), Figure 11 (approximate counts) and this replication.
            The ratio is compared because Figure 11’s absolute scale is unknown.
          </>
        }
        table={
          <DataTable
            rows={axisRatioRows(doc)}
            rowKey={(r) => r.key}
            columns={[
              { header: 'Sub-issue', cell: (r) => r.label },
              { header: '2012 ratio', cell: (r) => num(r.values.survey.value), numeric: true },
              { header: '2013–26 ratio', cell: (r) => num(r.values.pooled.value), numeric: true },
              { header: '95% CI', cell: (r) => ci(r.values.pooled.ci, 2), numeric: true },
            ]}
          />
        }
      >
        <IntervalChart
          rows={axisRatioRows(doc)}
          series={[
            { key: 'survey', label: '2012 survey', color: c.muted, hollow: true },
            { key: 'pooled', label: '2013–26 pooled', color: c.highlight },
          ]}
          domain={[0, 1.2]}
          ticks={[0, 0.3, 0.6, 0.9, 1.2]}
          yLabel="Solutions per concern"
          format={(v) => v.toFixed(2)}
        />
      </ChartCard>

      <section className="card results__block">
        <h3 className="card__title">Pre-registered hypotheses</h3>
        <ul className="results__hypotheses">
          {doc.hypotheses.map((h) => (
            <li key={h.id}>
              <StatusBadge status={BADGE[h.verdict].status} label={`${h.id} · ${BADGE[h.verdict].label}`} />
              <div>
                <p>{h.statement}</p>
                <p className="results__muted">{h.detail}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card results__block">
        <h3 className="card__title">Robustness: the virtualization gap under other counting choices</h3>
        <DataTable
          rows={robustnessRows(doc)}
          rowKey={(r) => r.id}
          columns={[
            {
              header: 'Variant',
              cell: (r) => (
                <>
                  <strong>{r.id === 'main' ? 'Main' : r.id}</strong>
                  <span className="replication__cell-note">{r.label}</span>
                </>
              ),
            },
            ...[...eras.map((e) => e.id), 'pooled'].map((p) => ({
              header: periodLabel(p),
              cell: (r: ReturnType<typeof robustnessRows>[number]) => (
                <>
                  {gapText(r.byPeriod[p]?.value)}
                  <span className="replication__cell-note">{ci(r.byPeriod[p]?.ci)}</span>
                </>
              ),
              numeric: true,
            })),
          ]}
        />
      </section>

      <ValidityCard doc={doc} />

      <ChartCard
        title="Virtualization CVEs per 10,000 published CVEs"
        subtitle="Descriptive supplement from the NVD: no hypothesis rests on it."
        caption={
          <>
            <strong>Source:</strong> {doc.cve.source}, snapshot {new Date(doc.cve.retrievedAt).toLocaleDateString()},{' '}
            {doc.cve.candidates.toLocaleString()} candidate CVEs; the last year is partial (hollow point). VM
            identification has no defensible CVE proxy and is not measured. {doc.cve.deviations.join(' ')}
          </>
        }
        table={
          <DataTable
            rows={cve}
            rowKey={(r) => String(r.year)}
            columns={[
              { header: 'Year', cell: (r) => `${r.year}${r.partial ? ' (partial)' : ''}` },
              { header: 'CVEs', cell: (r) => r.total.toLocaleString(), numeric: true },
              ...['any', 'virtualization-layer', ...subAxes].map((k) => ({
                header: CVE_AXIS_LABEL[k],
                cell: (r: (typeof cve)[number]) => num(r[k] as number | null, 1),
                numeric: true,
              })),
            ]}
          />
        }
      >
        <RateMultiples rows={cve} panels={[{ key: 'any', label: CVE_AXIS_LABEL.any }]} max={Math.ceil(maxOf(['any']))} color={c.highlight} />
        <RateMultiples
          rows={cve}
          panels={subAxes.map((k) => ({ key: k, label: CVE_AXIS_LABEL[k] }))}
          max={Math.ceil(maxOf(subAxes))}
          color={c.highlight}
        />
        {doc.cve.spotCheck && (
          <p className="results__muted replication__spot">
            Spot-check precision (20 random CVEs per axis):{' '}
            {Object.entries(doc.cve.spotCheck)
              .map(([k, s]) => `${CVE_AXIS_LABEL[k] ?? k} ${num(s.precisionWithD1)}`)
              .join(' · ')}
            .
          </p>
        )}
      </ChartCard>

      <section className="card results__block">
        <h3 className="card__title">Deviations and limitations</h3>
        <ul className="replication__list">
          {doc.protocol.deviations.map((d) => (
            <li key={d}>{d}</li>
          ))}
          {doc.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>

      <footer className="results__provenance">
        <strong>Provenance.</strong> Published {new Date(doc.generatedAt).toLocaleString()}. Rules frozen{' '}
        {new Date(doc.protocol.frozenAt).toLocaleString()} (<code>lexicon.py</code>{' '}
        <code>{doc.protocol.rulesSha256['lexicon.py']?.slice(0, 12)}</code>, <code>classify.py</code>{' '}
        <code>{doc.protocol.rulesSha256['classify.py']?.slice(0, 12)}</code>). OpenAlex query{' '}
        <code>{doc.protocol.query.slice(0, 48)}…</code>, {doc.protocol.samplePerEra.toLocaleString()} works per era;
        bootstrap B = {doc.protocol.bootstrapB}, seed {doc.protocol.bootstrapSeed}. Protocol and changelog in{' '}
        <a href="https://github.com/alpha08-prog/Cloud_Security/blob/main/docs/replication.md">docs/replication.md</a>.
      </footer>
    </div>
  )
}

function ValidityCard({ doc }: { doc: ReplicationResult }) {
  const w = doc.validation.weighted
  const sa = doc.validation.selfAgreement
  const cats = Object.keys(w.concern) as CategoryId[]
  return (
    <section className="card results__block">
      <h3 className="card__title">Validity: classifier vs blind human labels</h3>
      <p className="results__muted">
        {doc.validation.n} abstracts drawn after the freeze, stratified by classifier output and weighted back to the
        corpus (N<sub>h</sub>/n<sub>h</sub>); the annotator saw only titles and abstracts. Self-agreement on{' '}
        {sa.pairs} hidden repeats: category κ {num(sa.categoryKappa)}, type κ {num(sa.typeKappa)}.
      </p>
      <ul className="replication__checks">
        {Object.entries(w.validityGate.checks).map(([k, v]) => (
          <li key={k}>
            <StatusBadge status={v.met ? 'pass' : 'fail'} label={v.met ? 'Met' : 'Missed'} />
            <span>
              {VALIDITY_CHECK_LABEL[k] ?? k}: <strong className="num">{num(v.value)}</strong>{' '}
              <span className="results__muted">
                (≥ {v.threshold}; 95% CI {ci(w.ci?.[toCiKey(k)] ?? null, 2)})
              </span>
            </span>
          </li>
        ))}
      </ul>
      <DataTable
        rows={cats}
        rowKey={(k) => k}
        columns={[
          { header: 'Category (concern)', cell: (k) => getCategory(k).label },
          { header: 'Precision', cell: (k) => num(w.concern[k].precision), numeric: true },
          { header: 'Recall', cell: (k) => num(w.concern[k].recall), numeric: true },
          { header: 'F1', cell: (k) => num(w.concern[k].f1), numeric: true },
          { header: 'κ', cell: (k) => num(w.concern[k].kappa), numeric: true },
          { header: 'Solution F1', cell: (k) => num(w.solution[k].f1), numeric: true },
        ]}
      />
    </section>
  )
}

const toCiKey = (k: string) =>
  ({ macro_f1: 'macroF1', virtualization_f1: 'virtualizationF1', mean_kappa: 'meanKappa', type_kappa: 'typeKappa' })[
    k
  ] ?? k
