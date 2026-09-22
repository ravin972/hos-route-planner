import { z } from 'zod'

/** Mirrors the server's LocationInputSerializer bound (architecture.md section 6.1): exactly one
 * of {lat, lng} (from a selected typeahead suggestion) or {query} (free text), never both. This is
 * a UX-level check only -- the server re-validates everything (section 5.0). */
export const locationInputSchema = z
  .object({
    label: z.string().max(200).optional(),
    lat: z.number().min(-90).max(90).optional(),
    lng: z.number().min(-180).max(180).optional(),
    query: z.string().max(200).optional(),
  })
  .superRefine((value, ctx) => {
    const hasCoords = value.lat !== undefined || value.lng !== undefined
    const hasQuery = Boolean(value.query && value.query.length > 0)
    if (hasCoords && value.lat === undefined) {
      ctx.addIssue({ code: 'custom', path: ['lat'], message: 'Choose a suggestion from the list.' })
    }
    if (hasCoords && value.lng === undefined) {
      ctx.addIssue({ code: 'custom', path: ['lng'], message: 'Choose a suggestion from the list.' })
    }
    if (!hasCoords && !hasQuery) {
      ctx.addIssue({ code: 'custom', path: ['query'], message: 'Enter a location.' })
    }
  })

export const tripFormSchema = z.object({
  current_location: locationInputSchema,
  pickup_location: locationInputSchema,
  dropoff_location: locationInputSchema,
  cycle_used_hours: z
    .number('Enter the 70-hour cycle hours already used.')
    .min(0, 'Must be at least 0.')
    .max(70, 'Must be at most 70.'),
})

export type TripFormValues = z.infer<typeof tripFormSchema>

export const EMPTY_LOCATION: TripFormValues['current_location'] = {
  label: undefined,
  lat: undefined,
  lng: undefined,
  query: undefined,
}

export const defaultTripFormValues: TripFormValues = {
  current_location: { ...EMPTY_LOCATION },
  pickup_location: { ...EMPTY_LOCATION },
  dropoff_location: { ...EMPTY_LOCATION },
  cycle_used_hours: 0,
}
