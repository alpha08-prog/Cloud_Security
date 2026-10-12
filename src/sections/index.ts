import { lazy, type ComponentType } from 'react'

// Each section is its own chunk, loaded when its tab is first opened.
const Gap = lazy(() => import('./gap/Gap').then((m) => ({ default: m.Gap })))
const Requirements = lazy(() =>
  import('./requirements/Requirements').then((m) => ({ default: m.Requirements })),
)
const System = lazy(() => import('./system/System').then((m) => ({ default: m.System })))
const Results = lazy(() => import('./results/Results').then((m) => ({ default: m.Results })))
const Paper = lazy(() => import('./paper/Paper').then((m) => ({ default: m.Paper })))

export type SectionId = 'gap' | 'requirements' | 'system' | 'results' | 'paper'

export interface Section {
  id: SectionId
  /** Short tab label. */
  label: string
  title: string
  /** One-sentence takeaway shown under the title. */
  summary: string
  source: string
  badge?: string
  Component: ComponentType
}

// The story in order: the paper's finding, what it asks for, what we built, what we measured.
export const SECTIONS: readonly Section[] = [
  {
    id: 'gap',
    label: '1 · The gap',
    title: 'The gap the paper found',
    summary:
      'Across 200+ references, virtualization is the one area where solutions lag concerns: 12% of concern citations but 3% of solution citations. Inside it, isolation and cross-VM attacks are almost unanswered.',
    source: 'Gonzalez et al. (2012), Figures 6, 8 & 11',
    Component: Gap,
  },
  {
    id: 'requirements',
    label: '2 · Requirements',
    title: 'What the paper asks for',
    summary:
      'The paper’s own future-work section lists four requirements for the missing solution. IsoLab implements each one and verifies it with checks, detections and experiments.',
    source: 'Gonzalez et al. (2012), p.16 “Considerations and future work”',
    Component: Requirements,
  },
  {
    id: 'system',
    label: '3 · The system',
    title: 'IsoLab: what we built',
    summary:
      'A small multi-tenant cloud on one host: three tenants, a provider plane that audits, observes and detects, and two profiles, insecure and hardened, to compare.',
    source: 'This project · checks mapped to the paper’s taxonomy (Figures 2–4) and Tables 1–2',
    badge: 'Built, not described',
    Component: System,
  },
  {
    id: 'results',
    label: '4 · Results',
    title: 'What we measured',
    summary:
      'Measured, not claimed: the hardened profile closes every isolation path we probed, holds latency under a noisy neighbour, and detects every isolation-breaking action, attributed to the right tenant.',
    source: 'results/published (lab.py publish) · protocol in docs/experiments.md',
    Component: Results,
  },
  {
    id: 'paper',
    label: 'Paper',
    title: 'The paper, in detail',
    summary:
      'Appendix: the full taxonomy, every concern-vs-solution figure, the CSA / ENISA / NIST frameworks, and best-practice controls per category.',
    source: 'Gonzalez et al. (2012), Figures 1–11, Tables 1 & 2',
    Component: Paper,
  },
]

export const DEFAULT_SECTION: SectionId = 'gap'

/** Links from the earlier, explorer-style version of the site keep working. */
export const LEGACY_HASHES: Readonly<Record<string, string>> = {
  overview: 'gap',
  'side-channel': 'gap',
  data: 'paper/figures',
  taxonomy: 'paper/taxonomy',
  defenses: 'paper/controls',
  frameworks: 'paper/frameworks',
}

export function isSectionId(value: string): value is SectionId {
  return SECTIONS.some((section) => section.id === value)
}
