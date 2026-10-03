import { lazy, type ComponentType } from 'react'

// Each section is its own chunk, loaded when its tab is first opened.
const Overview = lazy(() => import('./overview/Overview').then((m) => ({ default: m.Overview })))
const Taxonomy = lazy(() => import('./taxonomy/Taxonomy').then((m) => ({ default: m.Taxonomy })))
const DataDashboard = lazy(() =>
  import('./data/DataDashboard').then((m) => ({ default: m.DataDashboard })),
)
const SideChannel = lazy(() =>
  import('./side-channel/SideChannel').then((m) => ({ default: m.SideChannel })),
)
const Defenses = lazy(() => import('./defenses/Defenses').then((m) => ({ default: m.Defenses })))
const Frameworks = lazy(() =>
  import('./frameworks/Frameworks').then((m) => ({ default: m.Frameworks })),
)

export type SectionId =
  | 'overview'
  | 'taxonomy'
  | 'data'
  | 'side-channel'
  | 'defenses'
  | 'frameworks'

export interface Section {
  id: SectionId
  /** Short tab label. */
  label: string
  title: string
  summary: string
  source: string
  badge?: string
  Component: ComponentType
}

// Summaries describe each section's scope (CLAUDE.md); figures and claims are
// taken from docs/paper-content.md.
export const SECTIONS: readonly Section[] = [
  {
    id: 'overview',
    label: 'Overview',
    title: 'Overview',
    summary:
      'The thesis at a glance: across 200+ references, most cloud-security concerns are matched by proposed solutions, except virtualization, which draws 12% of concern citations but only 3% of solution citations.',
    source: 'Gonzalez et al. (2012), Figures 6 & 8',
    Component: Overview,
  },
  {
    id: 'taxonomy',
    label: 'Taxonomy',
    title: 'Taxonomy explorer',
    summary:
      'Interactive, collapsible versions of the paper’s taxonomy: the three dimensions (Architecture, Compliance, Privacy) and the category trees beneath them.',
    source: 'Gonzalez et al. (2012), Figures 1–4',
    Component: Taxonomy,
  },
  {
    id: 'data',
    label: 'Data',
    title: 'Data dashboard',
    summary:
      'Concern vs. solution citation share for the seven categories, with the virtualization gap highlighted, plus sub-category and virtualization-radar views.',
    source: 'Gonzalez et al. (2012), Figures 5–8 & 11',
    Component: DataDashboard,
  },
  {
    id: 'side-channel',
    label: 'Side-channel',
    title: 'Cross-VM side-channel simulator',
    summary:
      'An educational model of the principle behind cross-VM attacks (co-residency → shared CPU cache → access-timing differences → statistical recovery of a made-up secret) and of the mitigations that defeat it.',
    source: 'Gonzalez et al. (2012), Figure 2 — Virtualization › Cross-VM attacks',
    badge: 'Conceptual model · synthetic data',
    Component: SideChannel,
  },
  {
    id: 'defenses',
    label: 'Defenses',
    title: 'Defense matrix',
    summary:
      'Concrete controls that answer each of the paper’s seven concern categories, filterable by category and dimension.',
    source: 'Categories from Gonzalez et al. (2012); controls are current best practice',
    Component: Defenses,
  },
  {
    id: 'frameworks',
    label: 'Frameworks',
    title: 'Frameworks',
    summary: 'Summaries of the CSA, ENISA, and NIST guidance the paper reviews.',
    source: 'Gonzalez et al. (2012), Tables 1 & 2',
    Component: Frameworks,
  },
]

export const DEFAULT_SECTION: SectionId = 'overview'

export function isSectionId(value: string): value is SectionId {
  return SECTIONS.some((section) => section.id === value)
}
