// Taxonomy (Figures 1–4), mirrored from docs/paper-content.md §1–4.

export type DimensionId = 'architecture' | 'compliance' | 'privacy'

export type CategoryId =
  | 'network-security'
  | 'interfaces'
  | 'virtualization'
  | 'governance'
  | 'compliance'
  | 'data-security'
  | 'legal-issues'

export interface Dimension {
  id: DimensionId
  label: string
  /** Figure holding this dimension's full tree. */
  figure: 2 | 3 | 4
  categories: readonly CategoryId[]
}

export interface Category {
  id: CategoryId
  label: string
  dimension: DimensionId
  /** Parenthetical detail shown next to the category in Figure 1, if any. */
  figure1Note?: string
}

export const DIMENSIONS: readonly Dimension[] = [
  {
    id: 'architecture',
    label: 'Architecture',
    figure: 2,
    categories: ['network-security', 'interfaces', 'virtualization'],
  },
  {
    id: 'compliance',
    label: 'Compliance',
    figure: 3,
    categories: ['governance', 'compliance'],
  },
  {
    id: 'privacy',
    label: 'Privacy',
    figure: 4,
    categories: ['data-security', 'legal-issues'],
  },
]

export const CATEGORIES: readonly Category[] = [
  { id: 'network-security', label: 'Network security', dimension: 'architecture' },
  { id: 'interfaces', label: 'Interfaces', dimension: 'architecture' },
  { id: 'virtualization', label: 'Virtualization', dimension: 'architecture' },
  {
    id: 'governance',
    label: 'Governance',
    dimension: 'compliance',
    figure1Note: 'data/security control, lock-in',
  },
  {
    id: 'compliance',
    label: 'Compliance',
    dimension: 'compliance',
    figure1Note: 'SLA, loss of service, audit',
  },
  { id: 'data-security', label: 'Data security', dimension: 'privacy' },
  { id: 'legal-issues', label: 'Legal issues', dimension: 'privacy' },
]

const dimensionById = new Map(DIMENSIONS.map((d) => [d.id, d]))
const categoryById = new Map(CATEGORIES.map((c) => [c.id, c]))

export const getDimension = (id: DimensionId): Dimension => dimensionById.get(id)!
export const getCategory = (id: CategoryId): Category => categoryById.get(id)!

/** The category the paper identifies as the largest unsolved gap. */
export const UNDER_SOLVED: CategoryId = 'virtualization'

// ---------------------------------------------------------------------------
// Trees

export interface TreeNode {
  /** Path-derived, unique within a figure (e.g. "architecture/virtualization/isolation"). */
  id: string
  label: string
  /** Parenthetical detail from the figure. */
  note?: string
  /** Set on the node that *is* one of the seven categories. */
  category?: CategoryId
  /** Set on the node that *is* one of the three dimensions. */
  dimension?: DimensionId
  /** Leaves called out in bold in the source (the cross-VM attack examples). */
  emphasis?: boolean
  children?: TreeNode[]
}

export interface TaxonomyFigure {
  figure: 1 | 2 | 3 | 4
  title: string
  root: TreeNode
}

type NodeSpec = Omit<TreeNode, 'id' | 'children'> & { children?: NodeSpec[] }

const slug = (label: string) =>
  label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')

function withIds(spec: NodeSpec, parentId = ''): TreeNode {
  const id = parentId ? `${parentId}/${slug(spec.label)}` : slug(spec.label)
  const { children, ...rest } = spec
  return children ? { ...rest, id, children: children.map((c) => withIds(c, id)) } : { ...rest, id }
}

/** A sub-category with plain leaf labels. */
const group = (label: string, leaves: string[]): NodeSpec => ({
  label,
  children: leaves.map((leaf) => ({ label: leaf })),
})

const categoryNode = (category: CategoryId, children?: NodeSpec[], label?: string): NodeSpec => {
  const c = getCategory(category)
  return { label: label ?? c.label, category, children }
}

// Figure 1 — three dimensions and their categories.
const figure1: NodeSpec = {
  label: 'Cloud security taxonomy',
  children: DIMENSIONS.map((d) => ({
    label: d.label,
    dimension: d.id,
    children: d.categories.map((id) => ({
      ...categoryNode(id),
      note: getCategory(id).figure1Note,
    })),
  })),
}

// Figure 2 — Architecture.
const figure2: NodeSpec = {
  label: 'Architecture',
  dimension: 'architecture',
  children: [
    categoryNode('network-security', [
      group('Transfer security', [
        'Distributed architectures',
        'Resource sharing',
        'VM synchronization',
        'Data in transit',
      ]),
      group('Firewalling', ['VM isolation', 'Filtering', 'DoS prevention', 'Adapted solutions']),
      group('Security configuration', [
        'Protocols',
        'Systems',
        'Technologies',
        'Performance',
        'Efficiency',
      ]),
    ]),
    categoryNode('interfaces', [
      group('API', ['Access virtualized elements', 'Libraries']),
      group('Administrative interface', [
        'Remote resources control',
        'VM management',
        'Coding',
        'Deploying',
        'Developing',
        'User access control',
        'Configurations',
      ]),
      group('User interface', ['Service usage', 'Resource usage']),
      group('Authentication', ['Enable access', 'Account types', 'Multi-tenancy']),
    ]),
    categoryNode('virtualization', [
      group('Isolation', ['Logical isolation', 'Physical isolation']),
      group('Hypervisor vulnerabilities', ['Virtualization', 'Proprietary solutions']),
      group('Data leakage', ['Confidentiality', 'Integrity']),
      group('VM identification', ['Multiple processes', 'Multiple resources', 'Multiple users']),
      {
        label: 'Cross-VM attacks',
        children: [
          { label: 'Cryptographic key stealing', emphasis: true },
          { label: 'VM placement / overlapping attacks', emphasis: true },
        ],
      },
    ]),
  ],
}

// Figure 3 — Compliance. "Service" holds the Compliance category's sub-categories
// (SLA, loss of service, audit — Figure 1); "Provider" is the Governance category.
const figure3: NodeSpec = {
  label: 'Compliance',
  dimension: 'compliance',
  children: [
    categoryNode(
      'compliance',
      [
        group('SLA', ['Availability', 'Procedures', 'Policies']),
        group('Loss of service', ['Service outage', 'Chain failures', 'Customer-side redundancy']),
        group('Audit', ['Security assessments', 'Transparency', 'API']),
      ],
      'Service',
    ),
    categoryNode(
      'governance',
      [
        group('Data control', ['Redundancy', 'Location', 'File systems', 'Configurations']),
        group('Security control', [
          'Mechanisms',
          'Loss of control over policies',
          'Gaps',
          'Customer-side assessments',
        ]),
        group('Lock-in', ['Standards', 'Migrations', 'Service termination']),
      ],
      'Provider',
    ),
  ],
}

// Figure 4 — Privacy.
const figure4: NodeSpec = {
  label: 'Privacy',
  dimension: 'privacy',
  children: [
    categoryNode('data-security', [
      group('Cryptography', ['Sensitive data', 'Regulations']),
      group('Redundancy', ['Data loss', 'Data integrity', 'Data availability']),
      group('Disposal', ['Data deletion', 'Data destruction', 'Log references', 'Hidden backups']),
    ]),
    categoryNode('legal-issues', [
      group('Data location', ['Multiple jurisdictions', 'Subpoena']),
      group('E-discovery', ['Law-enforcement measures', 'Hardware sharing']),
      group('Provider privilege', ['Malicious insiders', 'Privilege escalation']),
    ]),
  ],
}

export const TAXONOMY_FIGURES: readonly TaxonomyFigure[] = [
  { figure: 1, title: 'Three dimensions', root: withIds(figure1) },
  { figure: 2, title: 'Architecture', root: withIds(figure2) },
  { figure: 3, title: 'Compliance', root: withIds(figure3) },
  { figure: 4, title: 'Privacy', root: withIds(figure4) },
]

// ---------------------------------------------------------------------------
// Lookups

export interface NodeContext {
  node: TreeNode
  /** Root → node, inclusive. */
  path: TreeNode[]
  category?: CategoryId
  dimension?: DimensionId
}

/** Every node in a figure, keyed by id, with its ancestry resolved. */
export function indexFigure(figure: TaxonomyFigure): Map<string, NodeContext> {
  const index = new Map<string, NodeContext>()
  const visit = (node: TreeNode, path: TreeNode[]) => {
    const fullPath = [...path, node]
    const category = [...fullPath].reverse().find((n) => n.category)?.category
    const dimension =
      [...fullPath].reverse().find((n) => n.dimension)?.dimension ??
      (category ? getCategory(category).dimension : undefined)
    index.set(node.id, { node, path: fullPath, category, dimension })
    node.children?.forEach((child) => visit(child, fullPath))
  }
  visit(figure.root, [])
  return index
}

const subcategoryToCategory = new Map<string, CategoryId>()
for (const figure of TAXONOMY_FIGURES.slice(1)) {
  for (const category of figure.root.children ?? []) {
    for (const sub of category.children ?? []) {
      subcategoryToCategory.set(sub.label.toLowerCase(), category.category!)
    }
  }
}

/**
 * The category whose tree (Figures 2–4) contains a sub-category with this label,
 * matched case-insensitively. Places the sub-categories of Figures 5 & 7;
 * "Legislation" and "Service conformity" have no tree node, so return undefined.
 */
export const categoryOfSubcategory = (label: string): CategoryId | undefined =>
  subcategoryToCategory.get(label.toLowerCase())
