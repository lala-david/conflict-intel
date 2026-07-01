"use client";

import { useMemo, useState, useCallback } from "react";
import Link from "next/link";
import Map, {
  Source,
  Layer,
  NavigationControl,
  Popup,
  type MapLayerMouseEvent,
} from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import type { SpreadPoint } from "@/lib/types";
import { getCategoryMeta, formatNumber, formatDate } from "@/lib/utils";

export type { SpreadPoint };

const BASEMAP =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

interface Props {
  points: SpreadPoint[];
  height?: number;
}

const CIRCLE_PAINT = {
  "circle-radius": [
    "interpolate",
    ["linear"],
    ["zoom"],
    2, ["interpolate", ["linear"], ["get", "f"], 0, 3, 10, 5, 100, 8, 1000, 12],
    7, ["interpolate", ["linear"], ["get", "f"], 0, 5, 10, 8, 100, 14, 1000, 24],
  ],
  "circle-color": "#F04438",
  "circle-opacity": 0.75,
  "circle-stroke-color": "#FCA5A5",
  "circle-stroke-width": 1,
  "circle-stroke-opacity": 0.6,
} as const;

interface PopupState {
  longitude: number;
  latitude: number;
  point: SpreadPoint;
}

/** Plots a node's events on a map. Each dot is a real event — click for details. */
export function NodeSpreadMap({ points, height = 380 }: Props) {
  const [popup, setPopup] = useState<PopupState | null>(null);
  const [hovering, setHovering] = useState(false);

  const geojson = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: points.map((p, i) => ({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [p.longitude, p.latitude] },
        properties: { i, f: p.fatalities || 0 },
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
    const padLng = maxLng - minLng < 0.5 ? 1.5 : 0;
    const padLat = maxLat - minLat < 0.5 ? 1.5 : 0;
    return [
      [minLng - padLng, minLat - padLat],
      [maxLng + padLng, maxLat + padLat],
    ] as [[number, number], [number, number]];
  }, [points]);

  const onClick = useCallback(
    (e: MapLayerMouseEvent) => {
      const f = e.features?.[0];
      if (!f) {
        setPopup(null);
        return;
      }
      const i = f.properties?.i as number;
      const point = points[i];
      if (point) setPopup({ longitude: point.longitude, latitude: point.latitude, point });
    },
    [points],
  );

  if (!bounds) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <Map
        initialViewState={{ bounds, fitBoundsOptions: { padding: 56, maxZoom: 6 } }}
        style={{ width: "100%", height }}
        mapStyle={BASEMAP}
        minZoom={1.2}
        maxZoom={10}
        renderWorldCopies={false}
        dragRotate={false}
        touchZoomRotate={false}
        interactiveLayerIds={["spread-points"]}
        cursor={hovering ? "pointer" : "grab"}
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
        onClick={onClick}
      >
        <NavigationControl position="top-right" showCompass={false} />
        <Source id="spread" type="geojson" data={geojson}>
          <Layer id="spread-points" type="circle" paint={CIRCLE_PAINT as never} />
        </Source>

        {popup && (
          <Popup
            longitude={popup.longitude}
            latitude={popup.latitude}
            anchor="bottom"
            offset={14}
            closeButton
            closeOnClick={false}
            onClose={() => setPopup(null)}
            maxWidth="none"
          >
            <EventCard point={popup.point} />
          </Popup>
        )}
      </Map>
    </div>
  );
}

function EventCard({ point }: { point: SpreadPoint }) {
  const meta = getCategoryMeta(point.category);
  const place = [point.location, point.country].filter(Boolean).join(", ");
  return (
    <div className="w-60 rounded-lg border border-border bg-surface p-3 text-left shadow-xl">
      <div className="flex items-center gap-2 text-[10px]">
        <span
          className="inline-flex rounded-full px-2 py-0.5 font-semibold uppercase tracking-wider text-white"
          style={{ background: meta.color }}
        >
          {meta.label}
        </span>
        <span className="font-mono text-text-dim">{formatDate(point.date)}</span>
      </div>
      <div className="mt-2 text-sm font-medium text-text-primary">
        {point.actor1 || "Unknown"}
        {point.actor2 && point.actor2 !== "Civilians" && (
          <span className="text-text-dim"> vs {point.actor2}</span>
        )}
      </div>
      {place && <div className="mt-1 text-xs text-text-dim">{place}</div>}
      <div className="mt-2 flex items-center justify-between">
        <span className="font-display text-lg font-semibold text-accent">
          {formatNumber(point.fatalities)}
          <span className="ml-1 text-xs font-normal text-text-dim">killed</span>
        </span>
        <Link
          href={`/events/${encodeURIComponent(point.id)}`}
          className="text-xs font-medium text-accent hover:underline"
        >
          Details →
        </Link>
      </div>
    </div>
  );
}
