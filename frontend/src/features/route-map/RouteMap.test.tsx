import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import s3 from '../../test/fixtures/s3-multiday.json'
import s4 from '../../test/fixtures/s4-cycle-exhausted.json'
import type { TripPlan } from '../../types/trip'
import { RouteMap } from './RouteMap'

// Leaflet needs real browser layout (canvas/DOM measurement) that jsdom cannot provide -- mocked
// per the approved Phase 4 test strategy, not exercised with real layout in jsdom.
vi.mock('leaflet', () => ({
  default: { divIcon: vi.fn(() => ({})) },
}))

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  Polyline: () => <div data-testid="polyline" />,
  Marker: ({ children }: { children: ReactNode }) => <div data-testid="marker">{children}</div>,
  Popup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

const s4Plan = s4 as unknown as TripPlan
const s3Plan = s3 as unknown as TripPlan

describe('RouteMap', () => {
  it('renders exactly one marker per stop', () => {
    render(<RouteMap route={s3Plan.route} stops={s3Plan.stops} />)
    expect(screen.getAllByTestId('marker')).toHaveLength(s3Plan.stops.length)
  })

  it('includes a marker for the cycle_limit stop on a cycle_exhausted plan', () => {
    render(<RouteMap route={s4Plan.route} stops={s4Plan.stops} />)
    expect(s4Plan.stops.some((stop) => stop.type === 'cycle_limit')).toBe(true)
    expect(screen.getAllByTestId('marker')).toHaveLength(s4Plan.stops.length)
  })

  it('draws the route polyline', () => {
    render(<RouteMap route={s3Plan.route} stops={s3Plan.stops} />)
    expect(screen.getByTestId('polyline')).toBeInTheDocument()
  })
})
