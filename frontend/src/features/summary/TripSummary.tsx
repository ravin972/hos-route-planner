import { Alert } from '../../components/ui/Alert'
import { formatDateTime, formatDurationHM, formatHours, formatMiles } from '../../lib/format'
import type { TripSummaryData, TripWarning } from '../../types/trip'

interface TripSummaryProps {
  summary: TripSummaryData
  warnings: TripWarning[]
}

/** The four scannable-in-2-3-seconds headline metrics. Driving/on-duty use clock-style "17h 32m"
 * (elapsed time reads more naturally that way); cycle remaining stays decimal (an allowance
 * figure, not an elapsed duration) -- both are pure presentational formatting (lib/format.ts),
 * never a recomputation of the schedule itself (architecture.md section 5.0). */
export function TripSummary({ summary, warnings }: TripSummaryProps) {
  const isExhausted = summary.status === 'cycle_exhausted'
  const showPlannedDistance = summary.planned_distance_mi !== summary.route_distance_mi

  return (
    <div className="space-y-5">
      {isExhausted && warnings[0] && (
        <Alert variant="violation" title="Cycle exhausted before the trip finished">
          <p>{warnings[0].message}</p>
        </Alert>
      )}

      <dl className="grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
        <div>
          <dt className="text-label text-ink-tertiary">Route distance</dt>
          <dd className="text-metric mt-1 text-ink">{formatMiles(summary.route_distance_mi)}</dd>
        </div>
        <div>
          <dt className="text-label text-ink-tertiary">Driving time</dt>
          <dd className="text-metric mt-1 text-ink">
            {formatDurationHM(summary.total_driving_hours)}
          </dd>
        </div>
        <div>
          <dt className="text-label text-ink-tertiary">On-duty time</dt>
          <dd className="text-metric mt-1 text-ink">
            {formatDurationHM(summary.total_on_duty_hours)}
          </dd>
        </div>
        <div>
          <dt className="text-label text-ink-tertiary">Cycle remaining</dt>
          <dd className="text-metric mt-1 text-ink">{formatHours(summary.cycle.remaining_h)}</dd>
        </div>
      </dl>

      <dl className="flex flex-wrap gap-x-8 gap-y-2 border-t border-border pt-4">
        <div className="flex items-baseline gap-1.5">
          <dt className="text-label text-ink-tertiary">Departure</dt>
          <dd className="text-body text-ink">{formatDateTime(summary.departure_at)}</dd>
        </div>
        <div className="flex items-baseline gap-1.5">
          <dt className="text-label text-ink-tertiary">Arrival</dt>
          <dd className="text-body text-ink">
            {summary.arrival_at ? formatDateTime(summary.arrival_at) : 'Trip incomplete'}
          </dd>
        </div>
        <div className="flex items-baseline gap-1.5">
          <dt className="text-label text-ink-tertiary">Days</dt>
          <dd className="text-body text-ink">{summary.days}</dd>
        </div>
        {showPlannedDistance && (
          <div className="flex items-baseline gap-1.5">
            <dt className="text-label text-ink-tertiary">Planned distance</dt>
            <dd className="text-body text-ink">{formatMiles(summary.planned_distance_mi)}</dd>
          </div>
        )}
      </dl>

      <div className="text-caption flex flex-wrap gap-x-6 gap-y-1 text-ink-tertiary">
        <span>Fuel stops: {summary.stop_counts.fuel}</span>
        <span>30-min breaks: {summary.stop_counts.break}</span>
        <span>10-hour resets: {summary.stop_counts.rest}</span>
      </div>
    </div>
  )
}
