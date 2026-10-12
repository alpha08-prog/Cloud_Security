import { useEffect, useState } from 'react'

/**
 * A section's sub-view, kept in the URL hash as `#section/view` so any view can be
 * deep-linked in a demo. Uses replaceState: switching sub-views doesn't add history
 * entries or re-trigger the tab change in App.
 */
export function useSubview<T extends string>(
  section: string,
  views: readonly T[],
  fallback: T,
): [T, (view: T) => void] {
  const read = (): T => {
    const [s, sub] = window.location.hash.slice(1).split('/')
    return s === section && views.includes(sub as T) ? (sub as T) : fallback
  }
  const [view, setView] = useState<T>(read)

  useEffect(() => {
    const onHashChange = () => setView(read())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
    // read() only depends on stable arguments
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const select = (next: T) => {
    window.history.replaceState(null, '', `#${section}/${next}`)
    setView(next)
  }
  return [view, select]
}
