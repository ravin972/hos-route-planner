import { fireEvent, render, screen } from '@testing-library/react'
import { HttpResponse, delay, http } from 'msw'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'
import s1 from './test/fixtures/s1-complete.json'
import s4 from './test/fixtures/s4-cycle-exhausted.json'
import { server } from './test/server'

// Leaflet needs real browser layout that jsdom cannot provide -- mocked per the approved Phase 4
// test strategy (RouteMap renders on the App's success path).
vi.mock('leaflet', () => ({ default: { divIcon: vi.fn(() => ({})) } }))
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TileLayer: () => null,
  Polyline: () => null,
  Marker: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Popup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

function planAnExampleTrip() {
  fireEvent.click(screen.getByRole('button', { name: 'Try an example trip' }))
  fireEvent.click(screen.getByRole('button', { name: 'Plan trip' }))
}

describe('App trip-planning flow', () => {
  it('shows an idle prompt, then a loading state, then the success view for a complete trip', async () => {
    // An artificial delay widens the pending window enough to reliably observe it -- MSW's
    // in-memory default response is fast enough that the mutation can settle before the very
    // next microtask, which would make asserting the transient loading state itself flaky.
    server.use(
      http.post('/api/trips/plan', async () => {
        await delay(50)
        return HttpResponse.json(s1)
      }),
    )
    render(<App />)
    expect(screen.getByText(/Fill in the form above/)).toBeInTheDocument()

    planAnExampleTrip()
    expect(await screen.findByText(/Planning your trip/)).toBeInTheDocument()

    expect(await screen.findByText('Route distance')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Day 1' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows the violation banner and a single truncated day for a cycle_exhausted trip', async () => {
    server.use(http.post('/api/trips/plan', () => HttpResponse.json(s4)))
    render(<App />)

    planAnExampleTrip()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(s4.warnings[0]!.message)
    expect(screen.getByText('Trip incomplete')).toBeInTheDocument()
    // The log truncates at the cycle-exhausted stop -- exactly one day, no further days planned.
    expect(screen.getAllByRole('tab')).toHaveLength(1)
    expect(screen.getByRole('tab', { name: 'Day 1' })).toBeInTheDocument()
  })

  it('shows a retry-able error alert when the API returns an error envelope', async () => {
    server.use(
      http.post('/api/trips/plan', () =>
        HttpResponse.json(
          { error: { code: 'unroutable', message: 'no drivable route between the given points' } },
          { status: 422 },
        ),
      ),
    )
    render(<App />)

    planAnExampleTrip()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('no drivable route between the given points')
    expect(screen.getByRole('button', { name: 'Dismiss and try again' })).toBeInTheDocument()
  })
})
