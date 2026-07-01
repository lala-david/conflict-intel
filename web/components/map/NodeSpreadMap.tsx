"use client";

import { useMemo } from "react";
import Map, { Source, Layer, NavigationControl } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

const BASEMAP =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export interface SpreadPoint {
  longitude: number;
  latitude: number;
  fatalities: number;
}

interface Props {
  points: SpreadPoint[];
  height?: number;
}

const CIRCLE_PAINT = {
  "circle-radius": [
    "interpolate",
    ["linear"],
    ["get", "f"],
    0, 3,
    10, 5,
    100, 9,
    1000, 15,
  ],
  "circle-color": "#EF4444",
  "circle-opacity": 0.5,
  "circle-stroke-color": "#EF4444",
  "circle-stroke-width": 1,
  "circle-stroke-opacity": 0.9,
} as const;

/** Plots a node's events on a map, auto-fit to their spread. */
export function NodeSpreadMap({ points, height = 380 }: Props) {
  const geojson = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: points.map((p) => ({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [p.longitude, p.latitude] },
        properties: { f: p.fatalities || 0 },
      })),
    }),
    [points],
  );

  const bounds = useMemo(() => {
    if (points.length === 0) return null;
    let minLng = 180, minLat = 90, maxLng = -180, maxLat = -90;
    for (const p of points) {
      minLng = Math.min(minLng, p.longitude);
      maxLng = Math.max(maxLng, p.longitude);
      minLat = Math.min(minLat, p.latitude);
      maxLat = Math.max(maxLat, p.latitude);
    }
    // pad degenerate (single-point) bounds
    const padLng = maxLng - minLng < 0.5 ? 1.5 : 0;
    const padLat = maxLat - minLat < 0.5 ? 1.5 : 0;
    return [
      [minLng - padLng, minLat - padLat],
      [maxLng + padLng, maxLat + padLat],
    ] as [[number, number], [number, number]];
  }, [points]);

  if (!bounds) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <Map
        initialViewState={{ bounds, fitBoundsOptions: { padding: 56, maxZoom: 6 } }}
        style={{ width: "100%", height }}
        mapStyle={BASEMAP}
        minZoom={1.3}
        maxZoom={9}
        renderWorldCopies={false}
        maxBounds={[[-180, -78], [180, 84]]}
        dragRotate={false}
        touchZoomRotate={false}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <Source id="spread" type="geojson" data={geojson}>
          <Layer id="spread-points" type="circle" paint={CIRCLE_PAINT as never} />
        </Source>
      </Map>
    </div>
  );
}
