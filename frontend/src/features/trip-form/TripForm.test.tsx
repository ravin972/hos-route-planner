import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '../../test/renderWithProviders'
import { TripForm } from './TripForm'

describe('TripForm', () => {
  it('shows a validation error on each empty location field when submitted', async () => {
    const onSubmit = vi.fn()
    renderWithProviders(<TripForm onSubmit={onSubmit} />)

    fireEvent.click(screen.getByRole('button', { name: 'Plan trip' }))

    expect(await screen.findAllByText('Enter a location.')).toHaveLength(3)
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('selecting a typeahead suggestion with the keyboard commits its coordinates', async () => {
    const onSubmit = vi.fn()
    renderWithProviders(<TripForm onSubmit={onSubmit} />)

    const current = screen.getByLabelText('Current location')
    fireEvent.change(current, { target: { value: 'Chicago' } })

    const option = await screen.findByText('Chicago, Illinois')
    fireEvent.click(option)
    expect(current).toHaveValue('Chicago, Illinois')

    fireEvent.change(screen.getByLabelText('Pickup location'), {
      target: { value: 'St. Louis, MO' },
    })
    fireEvent.change(screen.getByLabelText('Drop-off location'), {
      target: { value: 'Dallas, TX' },
    })
    fireEvent.change(screen.getByLabelText('70-hour cycle used (hours)'), {
      target: { value: '10' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Plan trip' }))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    const payload = onSubmit.mock.calls[0]![0]
    expect(payload.current_location).toEqual({
      label: 'Chicago, Illinois',
      lat: 41.8756,
      lng: -87.6244,
      query: undefined,
    })
    expect(payload.pickup_location.query).toBe('St. Louis, MO')
    expect(payload.dropoff_location.query).toBe('Dallas, TX')
    expect(payload.cycle_used_hours).toBe(10)
  })

  it('"Try an example trip" fills every field and submits successfully', async () => {
    const onSubmit = vi.fn()
    renderWithProviders(<TripForm onSubmit={onSubmit} />)

    fireEvent.click(screen.getByRole('button', { name: 'Try an example trip' }))
    fireEvent.click(screen.getByRole('button', { name: 'Plan trip' }))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    const payload = onSubmit.mock.calls[0]![0]
    expect(payload.current_location.label).toBe('Chicago, IL')
    expect(payload.pickup_location.label).toBe('St. Louis, MO')
    expect(payload.dropoff_location.label).toBe('Dallas, TX')
    expect(payload.cycle_used_hours).toBe(32.5)
  })

  it('disables the submit button while isSubmitting is true', () => {
    renderWithProviders(<TripForm onSubmit={vi.fn()} isSubmitting />)
    expect(screen.getByRole('button', { name: /Plan trip/ })).toBeDisabled()
  })
})
