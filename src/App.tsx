import { Suspense, useEffect, useState } from 'react'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { SectionFrame } from './components/SectionFrame'
import { TabBar } from './components/TabBar'
import { panelId, tabId } from './components/tabIds'
import { useTheme } from './hooks/useTheme'
import { DEFAULT_SECTION, SECTIONS, isSectionId, type SectionId } from './sections'

// The active tab lives in the URL hash (#data, #side-channel, …) so sections can
// be deep-linked during a demo, the back button works, and static hosting needs
// no rewrite rules.
function sectionFromHash(): SectionId {
  const hash = window.location.hash.slice(1)
  return isSectionId(hash) ? hash : DEFAULT_SECTION
}

export default function App() {
  const { theme, toggle } = useTheme()
  const [activeId, setActiveId] = useState<SectionId>(sectionFromHash)

  useEffect(() => {
    const onHashChange = () => setActiveId(sectionFromHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const select = (id: SectionId) => {
    if (id !== activeId) window.location.hash = id
  }

  const active = SECTIONS.find((section) => section.id === activeId) ?? SECTIONS[0]
  const { Component } = active

  return (
    <>
      <Header theme={theme} onToggleTheme={toggle} />
      <TabBar items={SECTIONS} activeId={active.id} onSelect={select} />
      <main
        className="container"
        role="tabpanel"
        id={panelId(active.id)}
        aria-labelledby={tabId(active.id)}
        tabIndex={0}
      >
        <SectionFrame
          title={active.title}
          summary={active.summary}
          source={active.source}
          badge={active.badge}
        >
          <Suspense fallback={<p className="section-loading">Loading…</p>}>
            <Component />
          </Suspense>
        </SectionFrame>
      </main>
      <Footer />
    </>
  )
}
