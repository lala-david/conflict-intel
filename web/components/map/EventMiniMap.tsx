"use client";

import { useMemo } from "react";
import Map, { Marker, NavigationControl } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

const BASEMAP =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

interface Props {
  latitude: number;
  longitude: number;
  label?: string;
}

export function EventMiniMap({ latitude, longitude, label }: Props) {
  const viewState = useMemo(
    () => ({
      longitude,
      latitude,
      zoom: 6,
    }),
    [latitude, longitude]
  );

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <Map
        initialViewState={viewState}
        style={{ width: "100%", height: 240 }}
        mapStyle={BASEMAP}
        scrollZoom={false}
        dragPan={false}
        touchZoomRotate={false}
        doubleClickZoom={false}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <Marker longitude={longitude} latitude={latitude} anchor="center">
          <div className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-accent shadow-lg">
            <div className="h-2 w-2 rounded-full bg-white" />
          </div>
        </Marker>
      </Map>
      {label && (
        <div className="bg-surface px-3 py-2 text-xs text-text-dim">
          {latitude.toFixed(4)}, {longitude.toFixed(4)} · {label}
        </div>
      )}
    </div>
  );
}
