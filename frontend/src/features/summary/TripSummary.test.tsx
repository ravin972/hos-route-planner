import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import s1 from '../../test/fixtures/s1-complete.json'
import s4 from '../../test/fixtures/s4-cycle-exhausted.json'
import type { TripPlan } from '../../types/trip'
import { TripSummary } from './TripSummary'

const complete = s1 as unknown as TripPlan
const exhausted = s4 as unknown as TripPlan

describe('TripSummary', () => {
  it('renders no violation banner for a complete trip', () => {
    render(<TripSummary summary={complete.summary} warnings={complete.warnings} />)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows the arrival timestamp for a complete trip', () => {
    render(<TripSummary summary={complete.summary} warnings={complete.warnings} />)
    expect(screen.queryByText('Trip incomplete')).not.toBeInTheDocument()
  })

  it('renders the violation banner verbatim from warnings[0] for a cycle_exhausted trip', () => {
    render(<TripSummary summary={exhausted.summary} warnings={exhausted.warnings} />)
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent(exhausted.warnings[0]!.message)
  })

  it('shows "Trip incomplete" when arrival_at is null', () => {
    expect(exhausted.summary.arrival_at).toBeNull()
    render(<TripSummary summary={exhausted.summary} warnings={exhausted.warnings} />)
    expect(screen.getByText('Trip incomplete')).toBeInTheDocument()
  })
})
