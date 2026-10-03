import { useEffect, useRef, type KeyboardEvent } from 'react'
import { panelId, tabId } from './tabIds'
import './TabBar.css'

export interface TabItem<Id extends string> {
  id: Id
  label: string
}

interface TabBarProps<Id extends string> {
  items: readonly TabItem<Id>[]
  activeId: Id
  onSelect: (id: Id) => void
}

/** WAI-ARIA tabs: roving tabindex, arrow keys / Home / End move between tabs. */
export function TabBar<Id extends string>({ items, activeId, onSelect }: TabBarProps<Id>) {
  const buttons = useRef(new Map<Id, HTMLButtonElement>())

  useEffect(() => {
    buttons.current.get(activeId)?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }, [activeId])

  const onKeyDown = (event: KeyboardEvent, index: number) => {
    let next: number
    switch (event.key) {
      case 'ArrowRight':
        next = (index + 1) % items.length
        break
      case 'ArrowLeft':
        next = (index - 1 + items.length) % items.length
        break
      case 'Home':
        next = 0
        break
      case 'End':
        next = items.length - 1
        break
      default:
        return
    }
    event.preventDefault()
    const { id } = items[next]
    onSelect(id)
    buttons.current.get(id)?.focus()
  }

  return (
    <nav className="tabbar" aria-label="Sections">
      <div className="container">
        <div className="tablist" role="tablist" aria-label="Sections">
          {items.map((item, index) => {
            const selected = item.id === activeId
            return (
              <button
                key={item.id}
                ref={(el) => {
                  if (el) buttons.current.set(item.id, el)
                  else buttons.current.delete(item.id)
                }}
                type="button"
                role="tab"
                id={tabId(item.id)}
                className="tab"
                aria-selected={selected}
                aria-controls={selected ? panelId(item.id) : undefined}
                tabIndex={selected ? 0 : -1}
                onClick={() => onSelect(item.id)}
                onKeyDown={(event) => onKeyDown(event, index)}
              >
                {item.label}
              </button>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
