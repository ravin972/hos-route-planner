import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LOG_GRID_GEOMETRY, buildLogPath } from '../../lib/logGeometry'
import s3 from '../../test/fixtures/s3-multiday.json'
import type { TripPlan } from '../../types/trip'
import { LogSheet } from './LogSheet'

const plan = s3 as unknown as TripPlan
const day1 = plan.daily_logs[0]!

describe('LogSheet', () => {
  it('renders all four duty-status rows', () => {
    const { container } = render(<LogSheet day={day1} />)
    for (const label of ['Off Duty', 'Sleeper Berth', 'Driving', 'On Duty (Not Driving)']) {
      expect(container.textContent).toContain(label)
    }
  })

  it("renders each row's total from the day's totals_h, summing to 24", () => {
    render(<LogSheet day={day1} />)
    expect(Object.values(day1.totals_h).reduce((a, b) => a + b, 0)).toBeCloseTo(24, 5)
    for (const total of Object.values(day1.totals_h)) {
      expect(screen.getAllByText(total.toFixed(2)).length).toBeGreaterThan(0)
    }
  })

  it('draws the duty-status ink line exactly as buildLogPath computes for these segments', () => {
    const { container } = render(<LogSheet day={day1} />)
    const path = container.querySelector('svg path')
    const expected = buildLogPath(day1.segments, LOG_GRID_GEOMETRY)
    expect(path).not.toBeNull()
    expect(path?.getAttribute('d')).toBe(expected)
  })

  it('renders the remarks table with the same remarks the API returned', () => {
    render(<LogSheet day={day1} />)
    for (const remark of day1.remarks) {
      expect(screen.getAllByText(remark.note).length).toBeGreaterThan(0)
    }
  })
})
