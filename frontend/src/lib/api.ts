/**
 * Typed fetch wrapper: base URL + the one error envelope (architecture.md section 4.4,
 * `{"error": {"code", "message", "fields"?}}`) parsed into a typed `AppError`. Every hook and
 * feature calls through here, never `fetch` directly.
 */

import type { components } from '../types/api'
import type { LocationSearchResponse, TripPlan } from '../types/trip'

export type PlanRequest = components['schemas']['PlanRequest']

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export interface ApiErrorBody {
  code: string
  message: string
  fields?: Record<string, unknown>
}

/** Every failure mode this API can produce, including a network failure with no HTTP response
 * (`status` 0, `code` "network_error") so callers never have to special-case that separately. */
export class AppError extends Error {
  readonly status: number
  readonly code: string
  readonly fields?: Record<string, unknown>

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'AppError'
    this.status = status
    this.code = body.code
    this.fields = body.fields
  }
}

function isErrorEnvelope(value: unknown): value is { error: ApiErrorBody } {
  if (typeof value !== 'object' || value === null || !('error' in value)) return false
  const error = (value as { error: unknown }).error
  return (
    typeof error === 'object' &&
    error !== null &&
    typeof (error as { code?: unknown }).code === 'string' &&
    typeof (error as { message?: unknown }).message === 'string'
  )
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new AppError(0, {
      code: 'network_error',
      message: 'Could not reach the server. Check your connection and try again.',
    })
  }

  let body: unknown
  try {
    body = response.status === 204 ? null : await response.json()
  } catch {
    body = null
  }

  if (!response.ok) {
    if (isErrorEnvelope(body)) throw new AppError(response.status, body.error)
    throw new AppError(response.status, {
      code: 'error',
      message: `Request failed with status ${response.status}`,
    })
  }

  return body as T
}

export function planTrip(payload: PlanRequest): Promise<TripPlan> {
  return request<TripPlan>('/api/trips/plan', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function searchLocations(query: string, limit: number): Promise<LocationSearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) })
  return request<LocationSearchResponse>(`/api/locations/search?${params.toString()}`)
}
