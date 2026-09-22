import { formatMiles } from '../../lib/format'
import type { RouteLeg } from '../../types/trip'

const LEG_TITLE: Record<RouteLeg['kind'], string> = {
  to_pickup: 'To pickup',
  to_dropoff: 'To drop-off',
}

export function RouteInstructions({ legs }: { legs: RouteLeg[] }) {
  return (
    <div className="space-y-2">
      {legs.map((leg, legIndex) => (
        <details key={legIndex} className="rounded-sm border border-border">
          <summary className="text-body cursor-pointer select-none px-3 py-2 font-medium text-ink">
            {LEG_TITLE[leg.kind]} &middot; {formatMiles(leg.distance_mi)}
          </summary>
          <ol className="text-caption space-y-1 border-t border-border px-3 py-2 text-ink-secondary">
            {leg.steps.map((step, stepIndex) => (
              <li key={stepIndex} className="flex justify-between gap-2">
                <span>{step.instruction}</span>
                <span className="font-mono shrink-0 text-ink-tertiary">
                  {formatMiles(step.distance_mi)}
                </span>
              </li>
            ))}
          </ol>
        </details>
      ))}
    </div>
  )
}
