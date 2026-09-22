import { describe, expect, it } from 'vitest'
import {
  ROW_ORDER,
  buildLogPath,
  generateTicks,
  minuteToX,
  rowCenterY,
  statusToRowIndex,
} from './logGeometry'
import type { DailyLogSegment } from '../types/trip'

const GEOMETRY = { gridLeft: 100, gridTop: 0, gridWidth: 900, rowHeight: 40 }

describe('minuteToX', () => {
  it('maps minute 0 to gridLeft and minute 1440 to the right edge', () => {
    expect(minuteToX(0, GEOMETRY)).toBe(100)
    expect(minuteToX(1440, GEOMETRY)).toBe(1000)
  })

  it('maps noon (720) to the horizontal midpoint', () => {
    expect(minuteToX(720, GEOMETRY)).toBe(550)
  })
})

describe('statusToRowIndex / rowCenterY', () => {
  it('orders rows Off Duty, Sleeper Berth, Driving, On Duty top to bottom', () => {
    expect(ROW_ORDER).toEqual(['OFF', 'SB', 'D', 'ON'])
    expect(statusToRowIndex('OFF')).toBe(0)
    expect(statusToRowIndex('ON')).toBe(3)
  })

  it('centers each row within its band', () => {
    expect(rowCenterY('OFF', GEOMETRY)).toBe(20)
    expect(rowCenterY('SB', GEOMETRY)).toBe(60)
  })
})

describe('buildLogPath', () => {
  it('returns an empty string for no segments', () => {
    expect(buildLogPath([], GEOMETRY)).toBe('')
  })

  it('draws a horizontal run for a single segment', () => {
    const segments: DailyLogSegment[] = [
      { status: 'OFF', start_min: 0, end_min: 480, kind: 'idle' },
    ]
    const path = buildLogPath(segments, GEOMETRY)
    expect(path).toBe(`M 100 20 L ${minuteToX(480, GEOMETRY)} 20`)
  })

  it('draws a vertical connector between two segments with different statuses', () => {
    const segments: DailyLogSegment[] = [
      { status: 'OFF', start_min: 0, end_min: 480, kind: 'idle' },
      { status: 'D', start_min: 480, end_min: 600, kind: 'drive' },
    ]
    const path = buildLogPath(segments, GEOMETRY)
    const x480 = minuteToX(480, GEOMETRY)
    const x600 = minuteToX(600, GEOMETRY)
    // OFF row (y=20) to D row (y=100): the connector is the "L x480 100" step at the same x.
    expect(path).toBe(`M 100 20 L ${x480} 20 L ${x480} 100 L ${x600} 100`)
  })
})

describe('generateTicks', () => {
  it('produces one tick every 15 minutes from 0 to 1440', () => {
    const ticks = generateTicks(GEOMETRY)
    expect(ticks).toHaveLength(97)
    expect(ticks[0]?.minute).toBe(0)
    expect(ticks.at(-1)?.minute).toBe(1440)
  })

  it('weights hour ticks "hour", half-hours "half", others "quarter"', () => {
    const ticks = generateTicks(GEOMETRY)
    const byMinute = new Map(ticks.map((t) => [t.minute, t]))
    expect(byMinute.get(0)?.weight).toBe('hour')
    expect(byMinute.get(60)?.weight).toBe('hour')
    expect(byMinute.get(90)?.weight).toBe('half')
    expect(byMinute.get(75)?.weight).toBe('quarter')
  })

  it('labels midnight and noon distinctly from other hour ticks', () => {
    const ticks = generateTicks(GEOMETRY)
    const byMinute = new Map(ticks.map((t) => [t.minute, t]))
    expect(byMinute.get(0)?.label).toBe('Midnight')
    expect(byMinute.get(720)?.label).toBe('Noon')
    expect(byMinute.get(1440)?.label).toBe('Midnight')
    expect(byMinute.get(60)?.label).toBe('1')
  })
})
