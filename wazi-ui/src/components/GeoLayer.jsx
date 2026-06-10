import { useEffect, useState } from 'react';
import { GeoJSON } from 'react-leaflet';

const baseStyle = {
  color: '#2563eb',
  weight: 1,
  fillOpacity: 0.35,
};

const hoverStyle = {
  color: '#f59e0b',
  weight: 2,
  fillOpacity: 0.55,
};

const selectedStyle = {
  color: '#16a34a',
  weight: 2,
  fillOpacity: 0.6,
};

const getFeatureKey = (feature) =>
  feature?.properties?.PCODE ||
  feature?.properties?.IEBC_WARDS ||
  feature?.properties?.FIRST_DIST ||
  feature?.properties?.NO ||
  'unknown';

const getFeatureLabel = (feature) =>
  feature?.properties?.IEBC_WARDS ||
  feature?.properties?.FIRST_DIST ||
  feature?.properties?.PCODE ||
  'Kenya boundary';

export default function GeoLayer({ selectedFeatureKey, onFeatureHover, onFeatureSelect, onFeatureClear }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/geo/kenya.geojson')
      .then((response) => response.json())
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) {
    return null;
  }

  return (
    <GeoJSON
      data={data}
      style={(feature) => {
        const key = getFeatureKey(feature);

        if (selectedFeatureKey && selectedFeatureKey === key) {
          return selectedStyle;
        }

        return baseStyle;
      }}
      onEachFeature={(feature, layer) => {
        const wardName = getFeatureLabel(feature);
        const district = feature?.properties?.FIRST_DIST;
        const province = feature?.properties?.FIRST_PROV;

        layer.bindTooltip(
          district ? `${wardName} • ${district}` : wardName,
          { sticky: true }
        );

        layer.on({
          mouseover: () => {
            layer.setStyle(hoverStyle);
            if (onFeatureHover) {
              onFeatureHover({
                key: getFeatureKey(feature),
                label: wardName,
                district,
                province,
              });
            }
          },
          mouseout: () => {
            layer.setStyle(
              selectedFeatureKey && selectedFeatureKey === getFeatureKey(feature)
                ? selectedStyle
                : baseStyle
            );
            if (onFeatureClear) {
              onFeatureClear();
            }
          },
          click: () => {
            layer.setStyle(selectedStyle);
            if (onFeatureSelect) {
              onFeatureSelect({
                key: getFeatureKey(feature),
                label: wardName,
                district,
                province,
              });
            }
          },
        });
      }}
    />
  );
}