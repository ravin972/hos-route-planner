/**
 * Presentational number/date formatting only -- no HOS thresholds, no schedule logic
 * (architecture.md section 5.0). Every value formatted here already arrived from the API.
 */

export function formatMiles(miles: number): string {
  return `${miles.toLocaleString('en-US', { maximumFractionDigits: 1, minimumFractionDigits: 1 })} mi`
}

export function formatHours(hours: number): string {
  return `${hours.toLocaleString('en-US', { maximumFractionDigits: 2, minimumFractionDigits: 2 })} h`
}

/** Decimal hours -> "17h 32m". Presentational only -- 60 is a generic clock constant, not an HOS
 * threshold. Used for elapsed-time metrics (driving, on-duty) where clock-style duration reads
 * more naturally than decimal hours. */
export function formatDurationHM(hours: number): string {
  const totalMinutes = Math.round(hours * 60)
  const h = Math.floor(totalMinutes / 60)
  const m = totalMinutes % 60
  return `${h}h ${String(m).padStart(2, '0')}m`
}

/** Every ISO string this module formats already carries the trip's own fixed local time (either
 * a full timestamp with the trip's UTC offset, e.g. "2026-09-23T08:00:00-05:00", or a date-only
 * "2026-09-23") -- architecture.md AD-11: "the client never does time-zone arithmetic". Reading it
 * with `new Date(iso)` and then formatting via `toLocaleString` without a `timeZone` override does
 * arithmetic anyway: `Date` re-projects the instant into the *viewer's* browser timezone (and a
 * date-only string parses as UTC midnight first), silently shifting the displayed wall-clock time
 * -- and sometimes the calendar date -- for any viewer outside the trip's own zone. Parsing the
 * literal digits and re-anchoring them to UTC before formatting with `timeZone: 'UTC'` displays
 * exactly the wall-clock value the API sent, independent of the viewer's timezone. */
function literalWallClockAsUtc(iso: string): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(iso)
  if (!match) throw new Error(`Not an ISO date/datetime: ${iso}`)
  const [, year, month, day, hour, minute] = match
  return new Date(
    Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour ?? 0), Number(minute ?? 0)),
  )
}

export function formatDateTime(iso: string): string {
  return literalWallClockAsUtc(iso).toLocaleString('en-US', {
    timeZone: 'UTC',
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatTime(iso: string): string {
  return literalWallClockAsUtc(iso).toLocaleString('en-US', {
    timeZone: 'UTC',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/** ISO timestamp -> "Tue, 6:30 PM". Used in the stops timeline, where the day matters (a
 * multi-day trip's stops span more than one calendar day) but the full date is more than needed. */
export function formatWeekdayTime(iso: string): string {
  return literalWallClockAsUtc(iso).toLocaleString('en-US', {
    timeZone: 'UTC',
    weekday: 'short',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatDate(iso: string): string {
  return literalWallClockAsUtc(iso).toLocaleDateString('en-US', {
    timeZone: 'UTC',
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/** Integer minute-of-local-day (0-1440) -> "H:MM AM/PM". Presentational only -- 60/24 are generic
 * clock constants, not HOS thresholds. */
export function formatMinuteOfDay(minute: number): string {
  const clamped = Math.max(0, Math.min(1440, minute))
  const totalMinutes = clamped % 1440
  const hour24 = Math.floor(totalMinutes / 60)
  const minutePart = totalMinutes % 60
  const period = hour24 < 12 ? 'AM' : 'PM'
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12
  return `${hour12}:${minutePart.toString().padStart(2, '0')} ${period}`
}
