import { UNDER_SOLVED, type TreeNode } from '../../data/taxonomy'
import { getShare } from '../../data/stats'
import { cx } from '../../lib/format'

interface TreeViewProps {
  root: TreeNode
  expanded: ReadonlySet<string>
  selectedId: string | null
  onToggle: (id: string) => void
  onSelect: (id: string) => void
}

/** Collapsible tree: branches are disclosure buttons, leaves are selectable. */
export function TreeView(props: TreeViewProps) {
  return (
    <ul className="tree">
      <TreeItem node={props.root} {...props} />
    </ul>
  )
}

interface TreeItemProps extends Omit<TreeViewProps, 'root'> {
  node: TreeNode
}

function TreeItem({ node, expanded, selectedId, onToggle, onSelect }: TreeItemProps) {
  const isLeaf = !node.children?.length
  const open = expanded.has(node.id)
  const underSolved = node.category === UNDER_SOLVED
  const childrenId = `tree-children-${node.id}`

  return (
    <li
      className={cx(
        'tree__item',
        isLeaf && 'tree__item--leaf',
        underSolved && 'is-under-solved',
        node.emphasis && 'is-emphasis',
      )}
    >
      <div className="tree__row">
        {isLeaf ? (
          <button
            type="button"
            className="tree__leaf"
            aria-current={node.id === selectedId || undefined}
            onClick={() => onSelect(node.id)}
          >
            <span className="tree__dot" aria-hidden="true" />
            <span className="tree__label">{node.label}</span>
            {node.note && <span className="tree__note">({node.note})</span>}
          </button>
        ) : (
          <button
            type="button"
            className="tree__toggle"
            aria-expanded={open}
            aria-controls={childrenId}
            onClick={() => onToggle(node.id)}
          >
            <Chevron />
            <span className="tree__label">{node.label}</span>
            {node.note && <span className="tree__note">({node.note})</span>}
            {!open && <span className="tree__count">{countLeaves(node)}</span>}
          </button>
        )}
        <NodeMeta node={node} />
      </div>

      {!isLeaf && (
        <ul id={childrenId} className="tree__children" hidden={!open}>
          {node.children!.map((child) => (
            <TreeItem
              key={child.id}
              node={child}
              expanded={expanded}
              selectedId={selectedId}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

function NodeMeta({ node }: { node: TreeNode }) {
  if (node.emphasis) {
    return <span className="badge badge--accent">Cross-VM example</span>
  }
  if (!node.category) return null
  const { concern, solution } = getShare(node.category)
  return (
    <span className="tree__meta">
      <span className="tree__stat" title="Share of concern / solution citations (Figs 6 & 8)">
        concern <span className="num">{concern}%</span> · solution{' '}
        <span className="num">{solution}%</span>
      </span>
      {node.category === UNDER_SOLVED && (
        <span className="badge badge--highlight">Under-solved</span>
      )}
    </span>
  )
}

function countLeaves(node: TreeNode): number {
  return node.children ? node.children.reduce((sum, c) => sum + countLeaves(c), 0) : 1
}

function Chevron() {
  return (
    <svg className="tree__chevron" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
      <path
        d="M6 4l4 4-4 4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
