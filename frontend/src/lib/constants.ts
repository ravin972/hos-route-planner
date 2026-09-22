/**
 * UI-only constants. No HOS numbers live here -- every duty-status limit, break interval and
 * cycle threshold is computed server-side and arrives as data (architecture.md section 5.0).
 */

/** Mirrors the color tokens in index.css/DESIGN.md as raw hex, for the few places (Leaflet's
 * pathOptions, inline SVG) that need a literal color value rather than a CSS class. */
export const PALETTE = {
  ink: '#14181f',
  inkSecondary: '#5b6472',
  accent: '#1d4ed8',
  danger: '#dc2626',
  surface: '#ffffff',
} as const

export const DUTY_STATUS_LABEL: Record<'OFF' | 'SB' | 'D' | 'ON', string> = {
  OFF: 'Off Duty',
  SB: 'Sleeper Berth',
  D: 'Driving',
  ON: 'On Duty (Not Driving)',
}

export const STOP_TYPE_LABEL: Record<string, string> = {
  start: 'Trip start',
  pretrip: 'Pre-trip inspection',
  pickup: 'Pickup',
  fuel: 'Fuel',
  break: '30-minute break',
  rest: '10-hour reset',
  dropoff: 'Drop-off',
  cycle_limit: 'Cycle limit reached',
  restart: '34-hour restart',
}

export const LOCATION_SEARCH_MIN_CHARS = 3
export const LOCATION_SEARCH_DEBOUNCE_MS = 250
