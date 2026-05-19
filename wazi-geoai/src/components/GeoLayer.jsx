import { GeoJSON } from 'react-leaflet'
import { useEffect, useState } from 'react'

export default function GeoLayer() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch('/geo/kenya.geojson')
      .then((res) => res.json())
      .then(setData)
  }, [])

  if (!data) return null

  return (
    <GeoJSON
      data={data}
      style={{
        color: '#2563eb',
        weight: 1,
        fillOpacity: 0.4,
      }}
    />
  )
}