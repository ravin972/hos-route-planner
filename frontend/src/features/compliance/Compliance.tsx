import { AlertTriangle, Check } from 'lucide-react'
import { cn } from '../../lib/cn'
import type { TripSummaryData, TripWarning } from '../../types/trip'

interface ComplianceProps {
  summary: TripSummaryData
  warnings: TripWarning[]
}

/** The 4 HOS rules named in the log-sheet/HOS domain. This component computes nothing -- it only
 * maps the server's own `summary.status` and `warnings[]` onto a per-rule display. A
 * `cycle_exhausted` result specifically means the 70-hour/8-day allowance ran out; the planner
 * never violates the 11-hour/14-hour/10-hour rules on the way there (hos-rules.md), so only the
 * cycle row is ever shown as exhausted -- the other three stay compliant whenever a plan exists at
 * all, because the backend's independent validator (architecture.md AD-13) already refuses to
 * return a plan that violates them. */
const RULES = [
  { key: 'drive11', label: '11-hour driving limit' },
  { key: 'window14', label: '14-hour duty window' },
  { key: 'reset10', label: '10-hour consecutive rest' },
  { key: 'cycle70', label: '70-hour / 8-day cycle' },
] as const

export function Compliance({ summary, warnings }: ComplianceProps) {
  const isExhausted = summary.status === 'cycle_exhausted'
  const violationMessage = warnings[0]?.message

  return (
    <div className="divide-border divide-y rounded-md border border-border">
      {RULES.map((rule) => {
        const violated = isExhausted && rule.key === 'cycle70'
        return (
          <div
            key={rule.key}
            className={cn('flex items-start gap-3 px-4 py-3', violated && 'bg-danger-tint')}
          >
            {violated ? (
              <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
            ) : (
              <Check aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-success" />
            )}
            <div className="min-w-0">
              <p className="text-body text-ink">{rule.label}</p>
              {violated && violationMessage && (
                <p className="text-caption mt-0.5 text-ink-secondary">{violationMessage}</p>
              )}
            </div>
          </div>
        )
      })}
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-label text-ink-tertiary">Status</span>
        <span
          className={cn('text-body font-semibold', isExhausted ? 'text-danger' : 'text-success')}
        >
          {isExhausted ? 'Cycle exhausted' : 'Compliant'}
        </span>
      </div>
    </div>
  )
}
