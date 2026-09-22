import { formatHours, formatMiles } from '../../lib/format'
import type { DailyLog } from '../../types/trip'

export function DailySummaryTable({ days }: { days: DailyLog[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="text-caption w-full min-w-[560px] text-left">
        <thead>
          <tr className="text-label border-b border-border text-ink-tertiary">
            <th scope="col" className="py-2 pr-4 font-medium">
              Day
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-medium">
              Driving
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-medium">
              On duty
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-medium">
              Off duty
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-medium">
              Sleeper
            </th>
            <th scope="col" className="py-2 pr-4 text-right font-medium">
              Miles
            </th>
            <th scope="col" className="py-2 text-right font-medium">
              Cycle remaining
            </th>
          </tr>
        </thead>
        <tbody className="divide-border divide-y">
          {days.map((day) => (
            <tr key={day.day_number}>
              <td className="py-2 pr-4 text-ink">{day.day_number}</td>
              <td className="text-ink-secondary font-mono py-2 pr-4 text-right tabular-nums">
                {formatHours(day.summary.driving_h)}
              </td>
              <td className="text-ink-secondary font-mono py-2 pr-4 text-right tabular-nums">
                {formatHours(day.summary.on_duty_h)}
              </td>
              <td className="text-ink-secondary font-mono py-2 pr-4 text-right tabular-nums">
                {formatHours(day.summary.off_duty_h)}
              </td>
              <td className="text-ink-secondary font-mono py-2 pr-4 text-right tabular-nums">
                {formatHours(day.summary.sleeper_h)}
              </td>
              <td className="text-ink-secondary font-mono py-2 pr-4 text-right tabular-nums">
                {formatMiles(day.summary.miles)}
              </td>
              <td className="text-ink-secondary font-mono py-2 text-right tabular-nums">
                {formatHours(day.summary.cycle_remaining_h)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
