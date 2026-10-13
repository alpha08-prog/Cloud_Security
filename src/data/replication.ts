// The replication's pre-registered design (docs/replication.md), shown as-is until the
// results are published, and the labels the results view uses.

/** HR1–HR5 as pre-registered (§5); verdicts come only from results/published/replication.json. */
export const REPLICATION_HYPOTHESES: readonly { id: string; statement: string }[] = [
  { id: 'HR1', statement: 'The virtualization gap persists: G_v(2023–26) < 0' },
  { id: 'HR2', statement: 'The gap is narrower than in 2012: G_v(2023–26) > −9' },
  { id: 'HR3', statement: 'Virtualization is still the most negative category in 2023–26' },
  {
    id: 'HR4',
    statement:
      'Isolation + cross-VM are the least answered sub-issues (pooled solution/concern ratio below the other three)',
  },
  { id: 'HR5', statement: 'Validity gate: the classifier agrees with the blind human labels' },
]

/** The method in four steps, for the pending state and the paper's method figure. */
export const REPLICATION_STEPS: readonly { title: string; body: string }[] = [
  {
    title: 'Sample the literature',
    body: '2,500 seeded OpenAlex works per era (2013–17, 2018–22, 2023–26) matching cloud ∧ (security ∨ privacy), committed as hashed snapshots.',
  },
  {
    title: 'Count like the survey',
    body: 'Each (abstract, Figure-5 sub-category) pair is a concern entry; abstracts that propose something add solution entries. Same share-of-entries metric, same gap.',
  },
  {
    title: 'Freeze, then validate blind',
    body: 'Keyword rules tuned on 180 dev abstracts, hashed, then checked against 100 blind human labels (+10 hidden repeats) drawn after the freeze.',
  },
  {
    title: 'Test pre-registered hypotheses',
    body: 'Cluster-bootstrap intervals per era, four robustness variants, and an NVD CVE trend as a descriptive supplement.',
  },
]

export const PERIOD_LABEL: Readonly<Record<string, string>> = {
  '2012': '2012 survey',
  '2013-2017': '2013–17',
  '2018-2022': '2018–22',
  '2023-2026': '2023–26',
  pooled: '2013–26 pooled',
}

export const CVE_AXIS_LABEL: Readonly<Record<string, string>> = {
  any: 'Any virtualization axis',
  'virtualization-layer': 'Virtualization layer',
  isolation: 'Isolation / escape',
  'cross-vm-attacks': 'Cross-VM (side channels)',
  'data-leakage': 'Data leakage',
}

export const VALIDITY_CHECK_LABEL: Readonly<Record<string, string>> = {
  macro_f1: 'Macro-F1 (concern, 7 categories)',
  virtualization_f1: 'Virtualization F1 (concern)',
  mean_kappa: "Mean Cohen's κ (concern)",
  type_kappa: "Type κ (solution vs concern)",
}
