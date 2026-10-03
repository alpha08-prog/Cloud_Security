import { getShare } from '../../data/stats'
import {
  UNDER_SOLVED,
  getCategory,
  getDimension,
  type CategoryId,
  type NodeContext,
  type TaxonomyFigure,
} from '../../data/taxonomy'
import { formatGap } from '../../lib/format'

interface NodeDetailsProps {
  figure: TaxonomyFigure
  context: NodeContext | null
  /** Jump from a Figure 1 category to its detailed tree. */
  onOpenCategory: (category: CategoryId) => void
}

export function NodeDetails({ figure, context, onOpenCategory }: NodeDetailsProps) {
  if (!context) {
    return (
      <div className="details details--empty">
        <p className="eyebrow">Selection</p>
        <p className="details__hint">
          Select any leaf to see its full label and where it sits in the taxonomy.
        </p>
        <ul className="details__legend">
          <li>
            <span className="badge badge--highlight">Under-solved</span> the paper’s largest
            concern-vs-solution gap
          </li>
          <li>
            <span className="badge badge--accent">Cross-VM example</span> the paper’s two cross-VM
            attack examples, inside the under-solved branch
          </li>
          <li>
            <span className="num">concern 12% · solution 3%</span> the category’s share of
            citations (Figs 6 &amp; 8)
          </li>
        </ul>
      </div>
    )
  }

  const { node, path, category, dimension } = context
  // Figures 2–4: root (dimension) › category › sub-category › leaf.
  const subcategory = figure.figure !== 1 && path.length >= 4 ? path[2] : undefined
  const categoryNode = path.find((n) => n.category)
  const categoryLabel = category ? getCategory(category).label : undefined
  const share = category ? getShare(category) : undefined

  return (
    <div className="details" aria-live="polite">
      <p className="eyebrow">
        Figure {figure.figure} · {figure.title}
      </p>
      <h3 className="details__title">{node.label}</h3>
      <ol className="details__path" aria-label="Path in the taxonomy">
        {path.map((n) => (
          <li key={n.id}>{n.label}</li>
        ))}
      </ol>

      <dl className="facts">
        {dimension && (
          <>
            <dt>Dimension</dt>
            <dd>{getDimension(dimension).label}</dd>
          </>
        )}
        {categoryLabel && (
          <>
            <dt>Category</dt>
            <dd>
              {categoryLabel}
              {categoryNode && categoryNode.label !== categoryLabel && (
                <span className="details__aside"> (“{categoryNode.label}” in Figure {figure.figure})</span>
              )}
            </dd>
          </>
        )}
        {subcategory && (
          <>
            <dt>Sub-category</dt>
            <dd>{subcategory.label}</dd>
          </>
        )}
      </dl>

      {share && categoryLabel && (
        <div className="details__share">
          <p className="eyebrow">{categoryLabel} · share of citations (Figs 6 &amp; 8)</p>
          <ShareBar label="Concern" value={share.concern} kind="concern" />
          <ShareBar label="Solution" value={share.solution} kind="solution" />
          <p className="details__gap">
            Gap (solution − concern):{' '}
            <strong className="num">{formatGap(share.gap)}</strong>
          </p>
        </div>
      )}

      {category === UNDER_SOLVED && (
        <div className="callout callout--highlight">
          <p>
            Virtualization is the paper’s largest unsolved gap: 12% of concern citations but only
            3% of solution citations.
          </p>
        </div>
      )}

      <div className="details__actions">
        {figure.figure === 1 && category && (
          <button type="button" className="btn" onClick={() => onOpenCategory(category)}>
            Open in Figure {getDimension(getCategory(category).dimension).figure} →
          </button>
        )}
        {category === UNDER_SOLVED && (
          <a className="link-cta" href="#defenses">
            See the defenses for virtualization →
          </a>
        )}
      </div>
    </div>
  )
}

function ShareBar({
  label,
  value,
  kind,
}: {
  label: string
  value: number
  kind: 'concern' | 'solution'
}) {
  // Category shares top out at 29%; scale bars to 30 so they stay comparable.
  const width = `${(value / 30) * 100}%`
  return (
    <div className="share-bar">
      <span className="share-bar__label">{label}</span>
      <span className="share-bar__track">
        <span className={`share-bar__fill share-bar__fill--${kind}`} style={{ width }} />
      </span>
      <span className="share-bar__value num">{value}%</span>
    </div>
  )
}
