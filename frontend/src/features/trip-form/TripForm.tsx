import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { Controller, useForm, type FieldErrors } from 'react-hook-form'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Field } from '../../components/ui/Field'
import { Spinner } from '../../components/ui/Spinner'
import type { PlanRequest } from '../../lib/api'
import { LocationCombobox, type LocationValue } from './LocationCombobox'
import { defaultTripFormValues, tripFormSchema, type TripFormValues } from './schema'

const EXAMPLE_VALUES: TripFormValues = {
  current_location: { label: 'Chicago, IL', lat: 41.8781, lng: -87.6298, query: undefined },
  pickup_location: { label: 'St. Louis, MO', lat: 38.627, lng: -90.1994, query: undefined },
  dropoff_location: { label: 'Dallas, TX', lat: 32.7767, lng: -96.797, query: undefined },
  cycle_used_hours: 32.5,
}

interface TripFormProps {
  onSubmit: (payload: PlanRequest) => void
  isSubmitting?: boolean
}

function locationErrorMessage(errors: FieldErrors<TripFormValues>, field: keyof TripFormValues) {
  const fieldErrors = errors[field] as
    | { query?: { message?: string }; lat?: { message?: string }; lng?: { message?: string } }
    | undefined
  return fieldErrors?.query?.message ?? fieldErrors?.lat?.message ?? fieldErrors?.lng?.message
}

export function TripForm({ onSubmit, isSubmitting }: TripFormProps) {
  const [exampleKey, setExampleKey] = useState(0)
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TripFormValues>({
    resolver: zodResolver(tripFormSchema),
    defaultValues: defaultTripFormValues,
  })

  function fillExample() {
    reset(EXAMPLE_VALUES)
    setExampleKey((key) => key + 1)
  }

  return (
    <form onSubmit={handleSubmit((values) => onSubmit(values))} aria-label="Plan a trip">
      <Card key={exampleKey} className="grid gap-5 sm:grid-cols-2">
        <Field
          label="Current location"
          htmlFor="current_location"
          error={locationErrorMessage(errors, 'current_location')}
        >
          <Controller
            control={control}
            name="current_location"
            render={({ field }) => (
              <LocationCombobox
                id="current_location"
                value={field.value as LocationValue}
                onChange={field.onChange}
                onBlur={field.onBlur}
                placeholder="City, ST"
                invalid={Boolean(locationErrorMessage(errors, 'current_location'))}
                describedBy="current_location-error"
              />
            )}
          />
        </Field>

        <Field
          label="Pickup location"
          htmlFor="pickup_location"
          error={locationErrorMessage(errors, 'pickup_location')}
        >
          <Controller
            control={control}
            name="pickup_location"
            render={({ field }) => (
              <LocationCombobox
                id="pickup_location"
                value={field.value as LocationValue}
                onChange={field.onChange}
                onBlur={field.onBlur}
                placeholder="City, ST"
                invalid={Boolean(locationErrorMessage(errors, 'pickup_location'))}
                describedBy="pickup_location-error"
              />
            )}
          />
        </Field>

        <Field
          label="Drop-off location"
          htmlFor="dropoff_location"
          error={locationErrorMessage(errors, 'dropoff_location')}
        >
          <Controller
            control={control}
            name="dropoff_location"
            render={({ field }) => (
              <LocationCombobox
                id="dropoff_location"
                value={field.value as LocationValue}
                onChange={field.onChange}
                onBlur={field.onBlur}
                placeholder="City, ST"
                invalid={Boolean(locationErrorMessage(errors, 'dropoff_location'))}
                describedBy="dropoff_location-error"
              />
            )}
          />
        </Field>

        <Field
          label="70-hour cycle used (hours)"
          htmlFor="cycle_used_hours"
          error={errors.cycle_used_hours?.message}
          hint="0 to 70, decimals allowed"
        >
          <input
            id="cycle_used_hours"
            type="number"
            min={0}
            max={70}
            step={0.1}
            aria-invalid={Boolean(errors.cycle_used_hours) || undefined}
            aria-describedby="cycle_used_hours-error"
            className="text-body w-full rounded-sm border border-border px-3 py-2 text-ink focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            {...register('cycle_used_hours', { valueAsNumber: true })}
          />
        </Field>
      </Card>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Spinner className="text-white" />}
          Plan trip
        </Button>
        <Button type="button" variant="ghost" onClick={fillExample} disabled={isSubmitting}>
          Try an example trip
        </Button>
      </div>
    </form>
  )
}
