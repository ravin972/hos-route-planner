import { Badge } from '../../components/ui/Badge'
import { STOP_TYPE_LABEL } from '../../lib/constants'
import { formatMiles, formatWeekdayTime } from '../../lib/format'
import type { Stop } from '../../types/trip'

const VIOLATION_TONE = new Set(['cycle_limit'])

export function StopsTimeline({ stops }: { stops: Stop[] }) {
  return (
    <ol className="space-y-0">
      {stops.map((stop, index) => {
        const isViolation = VIOLATION_TONE.has(stop.type)
        return (
          <li key={stop.id} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span
                className={
                  isViolation
                    ? 'mt-1.5 h-2 w-2 shrink-0 rounded-full bg-danger'
                    : 'mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent'
                }
                aria-hidden="true"
              />
              {index < stops.length - 1 && <span className="w-px flex-1 bg-border" />}
            </div>
            <div className="min-w-0 pb-5">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-body font-semibold text-ink">{stop.label}</p>
                <Badge tone={isViolation ? 'danger' : 'neutral'}>
                  {STOP_TYPE_LABEL[stop.type] ?? stop.type}
                </Badge>
              </div>
              <p className="text-caption mt-0.5 text-ink-secondary">
                {formatWeekdayTime(stop.arrive_at)}
                {stop.duration_min > 0 && ` · ${stop.duration_min} min`} &middot;{' '}
                {formatMiles(stop.route_mile)}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
