import polyline from '@mapbox/polyline'
import 'leaflet/dist/leaflet.css'
import { useMemo } from 'react'
import { MapContainer, Polyline, TileLayer } from 'react-leaflet'
import { PALETTE } from '../../lib/constants'
import type { Stop, TripRoute } from '../../types/trip'
import { StopMarker } from './StopMarker'

interface RouteMapProps {
  route: TripRoute
  stops: Stop[]
}

export function RouteMap({ route, stops }: RouteMapProps) {
  const positions = useMemo(() => polyline.decode(route.geometry), [route.geometry])

  return (
    <div className="h-[420px] w-full overflow-hidden rounded-lg border border-border sm:h-[520px]">
      <MapContainer bounds={route.bounds} className="h-full w-full" scrollWheelZoom={false}>
        {/* Tile failures degrade to a blank background with the route/markers still visible
            (architecture.md section 7's documented handling) -- no extra fallback code needed. */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polyline positions={positions} pathOptions={{ color: PALETTE.accent, weight: 3.5 }} />
        {stops.map((stop) => (
          <StopMarker key={stop.id} stop={stop} />
        ))}
      </MapContainer>
    </div>
  )
}
