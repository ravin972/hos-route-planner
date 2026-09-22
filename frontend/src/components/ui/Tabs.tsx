import { cn } from '../../lib/cn'

export interface TabItem {
  id: string
  label: string
}

interface TabsProps {
  items: TabItem[]
  activeId: string
  onChange: (id: string) => void
  'aria-label': string
}

export function Tabs({ items, activeId, onChange, 'aria-label': ariaLabel }: TabsProps) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className="flex flex-wrap gap-1 border-b border-border"
    >
      {items.map((item) => {
        const selected = item.id === activeId
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={selected}
            className={cn(
              'text-body -mb-px inline-flex min-h-11 items-center rounded-t-sm px-3 py-2 font-medium transition-colors md:min-h-0',
              selected
                ? 'border-b-2 border-accent text-ink'
                : 'border-b-2 border-transparent text-ink-secondary hover:text-ink',
            )}
            onClick={() => onChange(item.id)}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}
