/**
 * Pure geometry for the daily-log SVG grid (architecture.md section 5.4, AD-8). The only
 * computation this module does is minute -> x and status -> row: no duty-status limit, break
 * interval or cycle threshold is known here. This isolation is deliberate -- it is what the HOS
 * guard test (frontend/src/lib/hosGuard.test.ts) checks against.
 */

import type { DailyLogSegment, DutyStatus } from '../types/trip'

export interface LogGridGeometry {
  gridLeft: number
  gridTop: number
  gridWidth: number
  rowHeight: number
}

/** LogGrid's own chosen pixel geometry, kept here (not in LogGrid.tsx) so a component-only file
 * satisfies eslint-plugin-react-refresh's one-export-per-file rule, and so the S3-fixture LogSheet
 * test can recompute the same path independently via buildLogPath. */
export const LOG_GRID_GEOMETRY: LogGridGeometry = {
  gridLeft: 140,
  gridTop: 12,
  gridWidth: 820,
  rowHeight: 40,
}

/** Top-to-bottom row order on the paper form (hos-rules.md section 4). */
export const ROW_ORDER: readonly DutyStatus[] = ['OFF', 'SB', 'D', 'ON']

export function minuteToX(minute: number, geometry: LogGridGeometry): number {
  return geometry.gridLeft + (minute / 1440) * geometry.gridWidth
}

export function statusToRowIndex(status: DutyStatus): number {
  return ROW_ORDER.indexOf(status)
}

/** The y coordinate of the center of a duty-status row. */
export function rowCenterY(status: DutyStatus, geometry: LogGridGeometry): number {
  return geometry.gridTop + statusToRowIndex(status) * geometry.rowHeight + geometry.rowHeight / 2
}

/**
 * One continuous SVG path `d` for a day's duty-status ink line. Consecutive segments are
 * contiguous (`segments[i].end_min === segments[i+1].start_min`), so emitting each segment's
 * start and end point as one polyline produces the horizontal run *and* the vertical connector
 * between differing statuses for free -- no separate connector-drawing step is needed.
 */
export function buildLogPath(
  segments: readonly DailyLogSegment[],
  geometry: LogGridGeometry,
): string {
  if (segments.length === 0) return ''

  const points: Array<[number, number]> = []
  for (const segment of segments) {
    const y = rowCenterY(segment.status, geometry)
    points.push([minuteToX(segment.start_min, geometry), y])
    points.push([minuteToX(segment.end_min, geometry), y])
  }

  const [first, ...rest] = points
  const start = first as [number, number]
  const commands = rest.map(([x, y]) => `L ${x} ${y}`)
  return [`M ${start[0]} ${start[1]}`, ...commands].join(' ')
}

export type TickWeight = 'hour' | 'half' | 'quarter'

export interface GridTick {
  minute: number
  x: number
  weight: TickWeight
  label?: string
}

const HOUR_LABELS = [
  'Midnight',
  '1',
  '2',
  '3',
  '4',
  '5',
  '6',
  '7',
  '8',
  '9',
  '10',
  '11',
  'Noon',
  '1',
  '2',
  '3',
  '4',
  '5',
  '6',
  '7',
  '8',
  '9',
  '10',
  '11',
  'Midnight',
]

/** Ticks every 15 minutes across the 24-hour grid, weighted hour/half-hour/quarter-hour. */
export function generateTicks(geometry: LogGridGeometry): GridTick[] {
  const ticks: GridTick[] = []
  for (let minute = 0; minute <= 1440; minute += 15) {
    const x = minuteToX(minute, geometry)
    if (minute % 60 === 0) {
      const label = HOUR_LABELS[minute / 60]
      ticks.push({ minute, x, weight: 'hour', label })
    } else if (minute % 30 === 0) {
      ticks.push({ minute, x, weight: 'half' })
    } else {
      ticks.push({ minute, x, weight: 'quarter' })
    }
  }
  return ticks
}
