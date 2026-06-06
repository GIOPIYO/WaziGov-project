import { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import GeoLayer from './GeoLayer';

function ResizeMap({ resizeToken }) {
  const map = useMap();
  const resizeObserverRef = useRef(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      map.invalidateSize({ animate: false });
    }, 200);

    return () => window.clearTimeout(timer);
  }, [map, resizeToken]);

  useEffect(() => {
    const container = map.getContainer();

    if (!container || typeof ResizeObserver === 'undefined') {
      return undefined;
    }

    resizeObserverRef.current = new ResizeObserver(() => {
      map.invalidateSize({ animate: false });
    });

    resizeObserverRef.current.observe(container);

    return () => {
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;
    };
  }, [map]);

  return null;
}

export default function MapView({
  selectedFeatureKey,
  onFeatureHover,
  onFeatureSelect,
  onFeatureClear,
  resizeToken,
}) {
  const kenyaBounds = [
    [-4.9, 33.8],
    [5.5, 41.9],
  ];

  return (
    <MapContainer
      bounds={kenyaBounds}
      maxBounds={kenyaBounds}
      maxBoundsViscosity={1.0}
      zoom={7}
      minZoom={6}
      maxZoom={14}
      scrollWheelZoom
      dragging
      worldCopyJump={false}
      attributionControl={false}
      zoomControl
      preferCanvas
      style={{
        height: '100%',
        width: '100%',
        background: '#dbeafe',
        minHeight: '100%',
      }}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        noWrap
        bounds={kenyaBounds}
      />
      <ResizeMap resizeToken={resizeToken} />
      <GeoLayer
        selectedFeatureKey={selectedFeatureKey}
        onFeatureHover={onFeatureHover}
        onFeatureSelect={onFeatureSelect}
        onFeatureClear={onFeatureClear}
      />
    </MapContainer>
  );
}