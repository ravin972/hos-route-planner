import L from 'leaflet'
import { Marker, Popup } from 'react-leaflet'
import { Badge } from '../../components/ui/Badge'
import { STOP_TYPE_LABEL } from '../../lib/constants'
import { formatMiles, formatTime } from '../../lib/format'
import type { Stop, StopType } from '../../types/trip'

// Matches DESIGN.md section 8: restrained, semantic marker colors -- not a distinct color per
// stop type. The popup text always names the stop type too (color is never the only signal).
const STOP_COLOR: Record<StopType, string> = {
  start: '#14181f',
  pretrip: '#5b6472',
  pickup: '#1d4ed8',
  fuel: '#5b6472',
  break: '#5b6472',
  rest: '#1d4ed8',
  dropoff: '#1d4ed8',
  cycle_limit: '#dc2626',
  restart: '#5b6472',
}

const ICONS = new Map<StopType, L.DivIcon>()

function iconFor(type: StopType): L.DivIcon {
  const cached = ICONS.get(type)
  if (cached) return cached
  const color = STOP_COLOR[type]
  const icon = L.divIcon({
    className: '',
    html: `<span style="display:block;width:16px;height:16px;border-radius:9999px;background:${color};border:2px solid white;box-shadow:0 0 0 1px rgba(0,0,0,0.25)"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    popupAnchor: [0, -8],
  })
  ICONS.set(type, icon)
  return icon
}

export function StopMarker({ stop }: { stop: Stop }) {
  return (
    <Marker position={[stop.lat, stop.lng]} icon={iconFor(stop.type)}>
      <Popup>
        <div className="text-body space-y-1">
          <p className="font-semibold text-ink">{STOP_TYPE_LABEL[stop.type] ?? stop.type}</p>
          <p className="text-caption text-ink-secondary">{stop.label}</p>
          <p className="text-caption text-ink-secondary">
            Arrive {formatTime(stop.arrive_at)} &middot; {stop.duration_min} min &middot;{' '}
            {formatMiles(stop.route_mile)}
          </p>
          <Badge tone="accent">{stop.duty_status}</Badge>
        </div>
      </Popup>
    </Marker>
  )
}
