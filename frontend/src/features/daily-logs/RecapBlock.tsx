import { formatHours } from '../../lib/format'
import type { DailyLogRecap } from '../../types/trip'

interface RecapBlockProps {
  recap: DailyLogRecap
}

export function RecapBlock({ recap }: RecapBlockProps) {
  return (
    <dl className="text-caption grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
      <div>
        <dt className="text-ink-tertiary">Total on duty today</dt>
        <dd className="font-mono mt-0.5 font-medium text-ink tabular-nums">
          {formatHours(recap.on_duty_today_h)}
        </dd>
      </div>
      <div>
        {/* blank-paper-log.png's "7/8 days" recap labels are transposed (CLAUDE.md); the 70-hour
            column is labelled "last 8 days" here, deliberately, to match that correction. */}
        <dt className="text-ink-tertiary">A. On duty, last 8 days</dt>
        <dd className="font-mono mt-0.5 font-medium text-ink tabular-nums">
          {formatHours(recap.a_last_8_days_h)}
        </dd>
      </div>
      <div>
        <dt className="text-ink-tertiary">B. Available tomorrow</dt>
        <dd className="font-mono mt-0.5 font-medium text-ink tabular-nums">
          {formatHours(recap.b_available_tomorrow_h)}
        </dd>
      </div>
      <div>
        <dt className="text-ink-tertiary">C. On duty, last 5 days</dt>
        <dd className="font-mono mt-0.5 font-medium text-ink tabular-nums">
          {recap.c_last_5_days_h === null ? '—' : formatHours(recap.c_last_5_days_h)}
        </dd>
      </div>
    </dl>
  )
}
