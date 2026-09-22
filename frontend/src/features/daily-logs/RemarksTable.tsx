import { formatMinuteOfDay } from '../../lib/format'
import type { DailyLogRemark } from '../../types/trip'

export function RemarksTable({ remarks }: { remarks: DailyLogRemark[] }) {
  if (remarks.length === 0) {
    return <p className="text-caption text-ink-tertiary">No remarks for this day.</p>
  }

  return (
    <table className="text-caption w-full text-left">
      <caption className="sr-only">Remarks: the text equivalent of the grid above</caption>
      <thead>
        <tr className="text-label border-b border-border text-ink-tertiary">
          <th scope="col" className="py-1.5 pr-4 font-medium">
            Time
          </th>
          <th scope="col" className="py-1.5 pr-4 font-medium">
            Place
          </th>
          <th scope="col" className="py-1.5 font-medium">
            Activity
          </th>
        </tr>
      </thead>
      <tbody className="divide-border divide-y">
        {remarks.map((remark, index) => (
          <tr key={index}>
            <td className="text-ink-secondary font-mono py-1.5 pr-4 tabular-nums">
              {formatMinuteOfDay(remark.minute)}
            </td>
            <td className="text-ink-secondary py-1.5 pr-4">{remark.place}</td>
            <td className="text-ink-secondary py-1.5">{remark.note}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
