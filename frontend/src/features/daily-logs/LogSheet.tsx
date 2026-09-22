import { Card } from '../../components/ui/Card'
import { formatDate, formatMiles } from '../../lib/format'
import type { DailyLog } from '../../types/trip'
import { LogGrid } from './LogGrid'
import { RecapBlock } from './RecapBlock'
import { RemarksTable } from './RemarksTable'

export function LogSheet({ day }: { day: DailyLog }) {
  return (
    <Card className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 className="text-section text-ink">{formatDate(day.date)}</h3>
        <p className="text-caption text-ink-secondary">
          {day.from} &rarr; {day.to} &middot; {formatMiles(day.miles_driven)}
        </p>
      </div>

      <dl className="text-caption grid grid-cols-2 gap-x-6 gap-y-1 text-ink-tertiary sm:grid-cols-4">
        <div>
          <dt className="inline">Carrier: </dt>
          <dd className="inline text-ink-secondary">{day.header.carrier || '—'}</dd>
        </div>
        <div>
          <dt className="inline">Main office: </dt>
          <dd className="inline text-ink-secondary">{day.header.main_office || '—'}</dd>
        </div>
        <div>
          <dt className="inline">Home terminal: </dt>
          <dd className="inline text-ink-secondary">{day.header.home_terminal || '—'}</dd>
        </div>
        <div>
          <dt className="inline">Vehicle: </dt>
          <dd className="inline text-ink-secondary">{day.header.vehicle || '—'}</dd>
        </div>
      </dl>

      <LogGrid
        segments={day.segments}
        totals={day.totals_h}
        title={`Duty status, ${formatDate(day.date)}`}
      />

      <div className="grid gap-6 border-t border-border pt-6 sm:grid-cols-2">
        <div>
          <h4 className="text-label mb-2 text-ink-tertiary">Remarks</h4>
          <RemarksTable remarks={day.remarks} />
        </div>
        <div>
          <h4 className="text-label mb-2 text-ink-tertiary">Recap</h4>
          <RecapBlock recap={day.recap} />
        </div>
      </div>
    </Card>
  )
}
