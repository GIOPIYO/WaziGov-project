import {
  MapContainer,
  TileLayer
} from 'react-leaflet'

import GeoLayer from './GeoLayer'

export default function MapView() {

  // Strict Kenya bounds
  const kenyaBounds = [
    [-4.9, 33.8], // Southwest Kenya
    [5.5, 41.9],  // Northeast Kenya
  ]

  return (

    <MapContainer

      bounds={kenyaBounds}

      maxBounds={kenyaBounds}

      maxBoundsViscosity={1.0}

      zoom={7}

      minZoom={6}

      maxZoom={14}

      scrollWheelZoom={true}

      dragging={true}

      worldCopyJump={false}

      attributionControl={false}

      zoomControl={true}

      preferCanvas={true}

      style={{
        height: '100%',
        width: '100%',
        background: '#dbeafe',
      }}
    >

      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"

        noWrap={true}

        bounds={kenyaBounds}
      />

      {/* Ward / County GeoJSON Layers */}
      <GeoLayer />

    </MapContainer>
  )
}