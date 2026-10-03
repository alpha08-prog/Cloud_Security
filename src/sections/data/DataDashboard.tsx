import { useState } from 'react'
import { SegmentedControl } from '../../components/SegmentedControl'
import { CategoryView } from './CategoryView'
import { SubcategoryView } from './SubcategoryView'
import { VirtualizationView } from './VirtualizationView'
import './DataDashboard.css'

type View = 'categories' | 'subcategories' | 'virtualization'

const VIEW_OPTIONS = [
  {
    value: 'categories' as const,
    label: (
      <>
        Categories <span className="segmented__hint">· Figs 6 &amp; 8</span>
      </>
    ),
  },
  {
    value: 'subcategories' as const,
    label: (
      <>
        Sub-categories <span className="segmented__hint">· Figs 5 &amp; 7</span>
      </>
    ),
  },
  {
    value: 'virtualization' as const,
    label: (
      <>
        Virtualization <span className="segmented__hint">· Fig 11</span>
      </>
    ),
  },
]

export function DataDashboard() {
  const [view, setView] = useState<View>('categories')

  return (
    <div className="dashboard">
      <div className="toolbar">
        <SegmentedControl label="Data view" options={VIEW_OPTIONS} value={view} onChange={setView} />
        {view !== 'categories' && <span className="badge">Approximate values</span>}
      </div>
      {view === 'categories' && <CategoryView />}
      {view === 'subcategories' && <SubcategoryView />}
      {view === 'virtualization' && <VirtualizationView />}
    </div>
  )
}
