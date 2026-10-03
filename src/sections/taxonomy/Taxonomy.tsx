import { useMemo, useState } from 'react'
import { SegmentedControl } from '../../components/SegmentedControl'
import { PAPER } from '../../data/paper'
import {
  TAXONOMY_FIGURES,
  UNDER_SOLVED,
  getCategory,
  getDimension,
  indexFigure,
  type CategoryId,
  type TaxonomyFigure,
  type TreeNode,
} from '../../data/taxonomy'
import { NodeDetails } from './NodeDetails'
import { TreeView } from './TreeView'
import './Taxonomy.css'

type FigureNumber = TaxonomyFigure['figure']

const branchIds = (node: TreeNode): string[] =>
  node.children ? [node.id, ...node.children.flatMap(branchIds)] : []

/**
 * Initial expansion: Figure 1 fully open; Figures 2–4 open to category level,
 * with the under-solved virtualization branch open all the way down.
 */
function defaultExpanded(figure: TaxonomyFigure): Set<string> {
  if (figure.figure === 1) return new Set(branchIds(figure.root))
  const ids = new Set([figure.root.id])
  for (const category of figure.root.children ?? []) {
    ids.add(category.id)
    if (category.category === UNDER_SOLVED) branchIds(category).forEach((id) => ids.add(id))
  }
  return ids
}

const initialExpanded = () =>
  Object.fromEntries(TAXONOMY_FIGURES.map((f) => [f.figure, defaultExpanded(f)])) as Record<
    FigureNumber,
    Set<string>
  >

const FIGURE_OPTIONS = TAXONOMY_FIGURES.map((f) => ({
  value: f.figure,
  label: (
    <>
      Fig {f.figure} <span className="segmented__hint">· {f.title}</span>
    </>
  ),
}))

export function Taxonomy() {
  const [figureNumber, setFigureNumber] = useState<FigureNumber>(2)
  const [expanded, setExpanded] = useState(initialExpanded)
  const [selected, setSelected] = useState<Partial<Record<FigureNumber, string>>>({})

  const figure = TAXONOMY_FIGURES.find((f) => f.figure === figureNumber)!
  const index = useMemo(() => indexFigure(figure), [figure])
  const selectedId = selected[figureNumber] ?? null
  const context = selectedId ? (index.get(selectedId) ?? null) : null

  const setFigureExpanded = (ids: Set<string>, target = figureNumber) =>
    setExpanded((prev) => ({ ...prev, [target]: ids }))

  const toggle = (id: string) => {
    const next = new Set(expanded[figureNumber])
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setFigureExpanded(next)
  }

  const openCategory = (category: CategoryId) => {
    const target = TAXONOMY_FIGURES.find(
      (f) => f.figure === getDimension(getCategory(category).dimension).figure,
    )!
    const node = target.root.children?.find((c) => c.category === category)
    if (node) {
      setFigureExpanded(new Set([...expanded[target.figure], ...branchIds(node)]), target.figure)
    }
    setFigureNumber(target.figure)
  }

  return (
    <div className="taxonomy">
      <div className="toolbar">
        <SegmentedControl
          label="Taxonomy figure"
          options={FIGURE_OPTIONS}
          value={figureNumber}
          onChange={setFigureNumber}
        />
        <div className="toolbar__group">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setFigureExpanded(new Set(branchIds(figure.root)))}
          >
            Expand all
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setFigureExpanded(new Set([figure.root.id]))}
          >
            Collapse all
          </button>
        </div>
      </div>

      <div className="taxonomy__layout">
        <figure className="card taxonomy__tree">
          <div className="card__body">
            <TreeView
              root={figure.root}
              expanded={expanded[figureNumber]}
              selectedId={selectedId}
              onToggle={toggle}
              onSelect={(id) => setSelected((prev) => ({ ...prev, [figureNumber]: id }))}
            />
          </div>
          <figcaption className="figure-caption taxonomy__caption">
            <strong>
              Figure {figure.figure} — {figure.title}
              {figure.figure === 1 ? ' of the cloud security taxonomy' : ' tree'}.
            </strong>{' '}
            Redrawn from {PAPER.short}. Category shares from Figures 6 &amp; 8.
          </figcaption>
        </figure>

        <aside className="card taxonomy__details" aria-label="Selected node">
          <NodeDetails figure={figure} context={context} onOpenCategory={openCategory} />
        </aside>
      </div>
    </div>
  )
}
