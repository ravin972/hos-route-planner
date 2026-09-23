import { describe, expect, it } from 'vitest'
import { formatDate, formatDateTime, formatTime, formatWeekdayTime } from './format'

// Every value here already carries the trip's own fixed local time (architecture.md AD-11); these
// formatters must display it as-is, never re-projected into the viewer's browser timezone. Asserting
// exact strings pins that down regardless of which TZ the test runner happens to execute in.

describe('formatDateTime', () => {
  it('shows the literal wall-clock time embedded in the ISO offset', () => {
    expect(formatDateTime('2026-09-23T08:00:00-05:00')).toBe('Wed, Sep 23, 8:00 AM')
  })

  it('is unaffected by a positive UTC offset', () => {
    expect(formatDateTime('2026-09-23T18:30:00+05:30')).toBe('Wed, Sep 23, 6:30 PM')
  })
})

describe('formatTime', () => {
  it('shows the literal wall-clock time', () => {
    expect(formatTime('2026-09-23T08:15:00-05:00')).toBe('8:15 AM')
  })
})

describe('formatWeekdayTime', () => {
  it('shows the literal weekday and wall-clock time', () => {
    expect(formatWeekdayTime('2026-09-23T08:00:00-05:00')).toBe('Wed 8:00 AM')
  })
})

describe('formatDate', () => {
  it('shows the literal calendar date for a date-only ISO string', () => {
    expect(formatDate('2026-09-23')).toBe('Wednesday, Sep 23, 2026')
  })

  it('does not roll the date backward for a midnight-boundary date', () => {
    // A naive `new Date('2026-01-01')` parses as UTC midnight; formatting that in any
    // UTC-negative viewer timezone without a `timeZone` override would show "Dec 31, 2025".
    expect(formatDate('2026-01-01')).toBe('Thursday, Jan 1, 2026')
  })
})
