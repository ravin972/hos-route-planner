/**
 * Hand-maintained response types for `POST /api/trips/plan`.
 *
 * `types/api.ts` is generated from the OpenAPI schema (AD-12) and covers the *request* shape
 * exactly (`components["schemas"]["PlanRequest"]`). The response views document their body as
 * `OpenApiTypes.OBJECT` rather than a fully-typed output serializer -- a deliberate Phase 3
 * decision (see `trips/api/serializers.py`'s module docstring: re-running the response through an
 * output serializer would duplicate shaping work `services.plan_trip` already does correctly) --
 * so drf-spectacular, and therefore openapi-typescript, cannot produce a real response type. These
 * types mirror `docs/api-contract.md`'s `TripPlan` contract field-for-field instead.
 */

export type TripStatus = 'complete' | 'cycle_exhausted'
export type CycleStatus = 'ok' | 'exhausted'
export type DutyStatus = 'OFF' | 'SB' | 'D' | 'ON'
export type SegmentKind =
  'pretrip' | 'drive' | 'pickup' | 'dropoff' | 'fuel' | 'break' | 'rest' | 'restart' | 'idle'
export type StopType =
  'start' | 'pretrip' | 'pickup' | 'fuel' | 'break' | 'rest' | 'dropoff' | 'cycle_limit' | 'restart' // never appears via this API -- the internal 34h-restart option is always off (D-2)
export type Blocked = 'pretrip' | 'drive' | 'fuel' | 'pickup' | 'dropoff' | 'next_shift'
export type WarningSeverity = 'violation'

export interface Place {
  label: string
  lat: number
  lng: number
}

export interface CycleSummary {
  used_at_start_h: number
  used_at_end_h: number
  remaining_h: number
  limit_h: number
  status: CycleStatus
}

export interface UnplannedRemainder {
  miles: number
  pending: string[]
  blocked: Blocked
  shortfall_h: number
}

export interface TripSummaryData {
  status: TripStatus
  route_distance_mi: number
  planned_distance_mi: number
  total_driving_hours: number
  total_on_duty_hours: number
  departure_at: string
  arrival_at: string | null
  days: number
  timezone: string
  utc_offset: string
  stop_counts: { fuel: number; break: number; rest: number; restart: number }
  cycle: CycleSummary
  unplanned: UnplannedRemainder | null
}

export interface TripAssumptions {
  avg_speed_mph: number
  pickup_min: number
  dropoff_min: number
  pretrip_min: number
  fuel_stop_min: number
  fuel_interval_mi: number
  cycle_limit_h: number
  restart_applied: boolean
  departure_local_time: string
}

export interface RouteStep {
  instruction: string
  distance_mi: number
  road: string
}

export interface RouteLeg {
  kind: 'to_pickup' | 'to_dropoff'
  from: Place
  to: Place
  distance_mi: number
  steps: RouteStep[]
}

export interface TripRoute {
  geometry: string
  bounds: [[number, number], [number, number]]
  legs: RouteLeg[]
}

export interface Stop {
  id: string
  type: StopType
  reason: string
  label: string
  lat: number
  lng: number
  route_mile: number
  arrive_at: string
  depart_at: string
  duration_min: number
  duty_status: DutyStatus
}

export interface DailyLogHeader {
  carrier: string
  main_office: string
  home_terminal: string
  vehicle: string
}

export interface DailyLogSegment {
  status: DutyStatus
  start_min: number
  end_min: number
  kind: SegmentKind
}

export interface DailyLogRemark {
  minute: number
  place: string
  note: string
}

export interface DailyLogRecap {
  on_duty_today_h: number
  a_last_8_days_h: number
  b_available_tomorrow_h: number
  c_last_5_days_h: number | null
}

export interface DailyLogSummary {
  driving_h: number
  on_duty_h: number
  off_duty_h: number
  sleeper_h: number
  miles: number
  stop_ids: string[]
  cycle_remaining_h: number
}

export interface DailyLog {
  date: string
  day_number: number
  from: string
  to: string
  miles_driven: number
  header: DailyLogHeader
  totals_h: { OFF: number; SB: number; D: number; ON: number }
  segments: DailyLogSegment[]
  remarks: DailyLogRemark[]
  recap: DailyLogRecap
  summary: DailyLogSummary
}

export interface TripWarning {
  code: string
  severity: WarningSeverity
  message: string
  details: Record<string, unknown>
}

export interface TripPlan {
  summary: TripSummaryData
  assumptions: TripAssumptions
  route: TripRoute
  stops: Stop[]
  daily_logs: DailyLog[]
  warnings: TripWarning[]
}

export interface LocationSuggestion {
  label: string
  lat: number
  lng: number
}

export interface LocationSearchResponse {
  results: LocationSuggestion[]
}
