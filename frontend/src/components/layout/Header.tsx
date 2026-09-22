const NAV_ITEMS = [
  { href: '#trip-planner', label: 'Planner' },
  { href: '#route', label: 'Route' },
  { href: '#daily-logs', label: 'Daily logs' },
  { href: '#compliance', label: 'Compliance' },
]

export function Header() {
  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-8 gap-y-3 px-4 py-4 sm:px-6">
        <div>
          <h1 className="text-section text-ink">HOS Route Planner</h1>
          <p className="text-caption text-ink-tertiary">
            Trip planning · HOS compliance · Daily logs
          </p>
        </div>
        <nav aria-label="Sections" className="flex flex-wrap gap-x-6 gap-y-2">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="inline-flex min-h-11 items-center text-body text-ink-secondary transition-colors hover:text-ink md:min-h-0"
            >
              {item.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  )
}
