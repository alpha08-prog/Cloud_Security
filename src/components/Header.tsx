import { PAPER, formatAuthors } from '../data/paper'
import type { Theme } from '../hooks/useTheme'
import './Header.css'

interface HeaderProps {
  theme: Theme
  onToggleTheme: () => void
}

export function Header({ theme, onToggleTheme }: HeaderProps) {
  const nextTheme = theme === 'dark' ? 'light' : 'dark'

  return (
    <header className="site-header">
      <div className="container site-header__inner">
        <div className="site-header__top">
          <div className="brand">
            <ShieldIcon className="brand__mark" />
            <div>
              <h1 className="brand__title">Cloud Security Threat Lab</h1>
              <p className="brand__tagline">
                An interactive explorer of {PAPER.short}
              </p>
            </div>
          </div>

          <button
            type="button"
            className="theme-toggle"
            onClick={onToggleTheme}
            aria-label={`Switch to ${nextTheme} theme`}
            title={`Switch to ${nextTheme} theme`}
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
            <span className="theme-toggle__label">
              {nextTheme === 'dark' ? 'Dark' : 'Light'}
            </span>
          </button>
        </div>

        <p className="citation">
          <span className="citation__label">Source</span>
          {formatAuthors(PAPER.authors)} ({PAPER.year}). <cite>{PAPER.title}</cite>.{' '}
          <i>{PAPER.journal}</i>, {PAPER.volume}({PAPER.number}). {PAPER.license}.
        </p>
      </div>
    </header>
  )
}

function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 2.75 4.75 5.6v5.65c0 4.5 3.06 8.6 7.25 9.9 4.19-1.3 7.25-5.4 7.25-9.9V5.6L12 2.75Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M8.6 14.2h6.6a2.2 2.2 0 0 0 .2-4.39 3 3 0 0 0-5.8.6 1.9 1.9 0 0 0-1 3.79Z"
        fill="currentColor"
      />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true">
      <path
        d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5a8.5 8.5 0 1 0 10.7 10.7Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}
