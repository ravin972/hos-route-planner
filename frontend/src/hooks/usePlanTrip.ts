import { useMutation } from '@tanstack/react-query'
import { planTrip, type PlanRequest } from '../lib/api'
import type { TripPlan } from '../types/trip'

/** The mutation's cached data *is* the trip plan -- no re-derivation, no re-shaping
 * (architecture.md section 5.2: "results live in the mutation"). */
export function usePlanTrip() {
  return useMutation<TripPlan, Error, PlanRequest>({
    mutationFn: planTrip,
  })
}
