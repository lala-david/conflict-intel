"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Map, {
  Source,
  Layer,
  NavigationControl,
  Popup,
} from "react-map-gl/maplibre";
import type { MapLayerMouseEvent } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { useRouter } from "next/navigation";
import * as topojson from "topojson-client";
import type { Topology } from "topojson-specification";
import { CATEGORY_META } from "@/lib/utils";
import type { Category } from "@/lib/types";

const BASEMAP =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

const CATEGORIES: Category[] = [
  "war",
  "civil_war",
  "terrorism",
  "mass_atrocity",
  "state_violence",
  "cartel_violence",
  "communal_violence",
  "insurgency",
  "counterterrorism",
  "armed_violence",
];

// Our modern country names → Natural Earth (topojson) feature names, for the
// handful where the two differ. Without this the choropleth can't color them
// (it matches on the feature name), so e.g. DR Congo — often the highest-threat
// country — would render uncolored.
const TOPO_NAME_ALIAS: Record<string, string> = {
  "DR Congo": "Dem. Rep. Congo",
  "South Sudan": "S. Sudan",
  "Palestinian Territories": "Palestine",
  "Central African Republic": "Central African Rep.",
  "Bosnia-Herzegovina": "Bosnia and Herz.",
  "Ivory Coast": "Côte d'Ivoire",
};

// Threat color scale: green → yellow → orange → red
function threatColor(score: number): string {
  if (score >= 8) return "rgba(220, 38, 38, 0.6)";
  if (score >= 6) return "rgba(234, 88, 12, 0.5)";
  if (score >= 4) return "rgba(234, 179, 8, 0.4)";
  if (score >= 2) return "rgba(34, 197, 94, 0.3)";
  return "rgba(64, 64, 64, 0.15)";
}

interface CountryScore {
  country: string;
  country_code: string;
  threat_score: number;
  fatalities_90d: number;
  events_90d: number;
}

interface Props {
  countryScores: CountryScore[];
}

interface HoverInfo {
  longitude: number;
  latitude: number;
  country: string;
  fatalities?: number;
  events?: number;
  category?: string;
}

export function WorldMap({ countryScores }: Props) {
  const router = useRouter();
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);
  const [activeCats, setActiveCats] = useState<Set<string>>(
    new Set(CATEGORIES)
  );
  const [countriesGeo, setCountriesGeo] = useState<any>(null);
  const [hotspotsGeo, setHotspotsGeo] = useState<any>(null);
  const [eventCount, setEventCount] = useState(0);

  // Load TopoJSON and convert to GeoJSON with threat scores
  useEffect(() => {
    fetch("/geo/countries-110m.json")
      .then((r) => r.json())
      .then((topo: Topology) => {
        const geo = topojson.feature(
          topo,
          topo.objects.countries as any
        ) as any;

        // Build lookup by ISO numeric code
        const scoreByCode: Record<string, CountryScore> = {};
        for (const s of countryScores) {
          if (s.country_code) scoreByCode[s.country_code] = s;
        }

        // Enrich features with threat data
        for (const f of geo.features) {
          const isoNum = f.id;
          const match = countryScores.find(
            (s) =>
              s.country_code === isoNum ||
              s.country === f.properties?.name ||
              TOPO_NAME_ALIAS[s.country] === f.properties?.name
          );
          if (match) {
            f.properties = {
              ...f.properties,
              threat_score: match.threat_score,
              fatalities_90d: match.fatalities_90d,
              events_90d: match.events_90d,
              country_name: match.country,
              fillColor: threatColor(match.threat_score),
            };
          } else {
            f.properties = {
              ...f.properties,
              threat_score: 0,
              fatalities_90d: 0,
              events_90d: 0,
              fillColor: "rgba(64, 64, 64, 0.1)",
            };
          }
        }

        setCountriesGeo(geo);
      })
      .catch(console.error);
  }, [countryScores]);

  // Load hotspot events
  useEffect(() => {
    fetch("/api/hotspots")
      .then((r) => r.json())
      .then((data) => {
        setHotspotsGeo(data);
        setEventCount(data.features?.length ?? 0);
      })
      .catch(console.error);
  }, []);

  // Category filter expression for MapLibre
  const catFilter = useMemo(() => {
    if (activeCats.size === CATEGORIES.length) return undefined;
    if (activeCats.size === 0)
      return ["==", ["get", "category"], "__none__"] as any;
    return ["in", ["get", "category"], ["literal", [...activeCats]]] as any;
  }, [activeCats]);

  const onHoverCountry = useCallback(
    (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0];
      if (feature && feature.properties) {
        setHoverInfo({
          longitude: e.lngLat.lng,
          latitude: e.lngLat.lat,
          country:
            feature.properties.country_name ||
            feature.properties.name ||
            "Unknown",
          fatalities: feature.properties.fatalities_90d,
          events: feature.properties.events_90d,
        });
      } else {
        setHoverInfo(null);
      }
    },
    []
  );

  const onHoverPoint = useCallback((e: MapLayerMouseEvent) => {
    const feature = e.features?.[0];
    if (feature && feature.properties) {
      setHoverInfo({
        longitude: e.lngLat.lng,
        latitude: e.lngLat.lat,
        country: feature.properties.country || "Unknown",
        fatalities: feature.properties.fatalities,
        category: feature.properties.category,
      });
    }
  }, []);

  const onMouseLeave = useCallback(() => {
    setHoverInfo(null);
  }, []);

  const onClick = useCallback(
    (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0];
      if (!feature?.properties) return;
      const countryName =
        feature.properties.country_name ||
        feature.properties.country ||
        feature.properties.name;
      if (countryName) {
        router.push(`/countries/${encodeURIComponent(countryName)}`);
      }
    },
    [router]
  );

  return (
    <div className="relative overflow-hidden rounded-xl border border-border bg-surface">
      <Map
        initialViewState={{
          longitude: 20,
          latitude: 15,
          zoom: 1.8,
        }}
        style={{ width: "100%", height: 520 }}
        mapStyle={BASEMAP}
        interactiveLayerIds={["choropleth-fill", "events-points"]}
        onMouseMove={onHoverCountry}
        onMouseLeave={onMouseLeave}
        onClick={onClick}
        cursor={hoverInfo ? "pointer" : "grab"}
      >
        <NavigationControl position="top-right" showCompass={false} />

        {/* Choropleth: country polygons colored by threat level */}
        {countriesGeo && (
          <Source id="countries" type="geojson" data={countriesGeo}>
            <Layer
              id="choropleth-fill"
              type="fill"
              paint={{
                "fill-color": ["get", "fillColor"],
                "fill-opacity": 0.7,
              }}
            />
            <Layer
              id="choropleth-border"
              type="line"
              paint={{
                "line-color": "#404040",
                "line-width": 0.5,
              }}
            />
          </Source>
        )}

        {/* Heatmap + Points: event data */}
        {hotspotsGeo && (
          <Source id="events" type="geojson" data={hotspotsGeo}>
            <Layer
              id="events-heat"
              type="heatmap"
              maxzoom={6}
              filter={catFilter}
              paint={{
                "heatmap-weight": [
                  "interpolate",
                  ["linear"],
                  ["get", "fatalities"],
                  0,
                  0.1,
                  10,
                  0.5,
                  100,
                  1,
                ],
                "heatmap-intensity": [
                  "interpolate",
                  ["linear"],
                  ["zoom"],
                  0,
                  0.6,
                  6,
                  2,
                ],
                "heatmap-color": [
                  "interpolate",
                  ["linear"],
                  ["heatmap-density"],
                  0,
                  "rgba(0,0,0,0)",
                  0.1,
                  "rgba(109,40,217,0.4)",
                  0.3,
                  "rgba(220,38,38,0.6)",
                  0.6,
                  "rgba(234,88,12,0.8)",
                  1,
                  "rgba(250,204,21,1)",
                ],
                "heatmap-radius": [
                  "interpolate",
                  ["linear"],
                  ["zoom"],
                  0,
                  5,
                  6,
                  30,
                ],
              }}
            />
            <Layer
              id="events-points"
              type="circle"
              minzoom={4}
              filter={catFilter}
              paint={{
                "circle-radius": [
                  "interpolate",
                  ["linear"],
                  ["get", "fatalities"],
                  0,
                  3,
                  10,
                  5,
                  50,
                  8,
                  200,
                  14,
                ],
                "circle-color": [
                  "match",
                  ["get", "category"],
                  "war",
                  "#991b1b",
                  "civil_war",
                  "#dc2626",
                  "terrorism",
                  "#6d28d9",
                  "mass_atrocity",
                  "#7f1d1d",
                  "state_violence",
                  "#db2777",
                  "cartel_violence",
                  "#d97706",
                  "communal_violence",
                  "#0d9488",
                  "insurgency",
                  "#2563eb",
                  "counterterrorism",
                  "#16a34a",
                  "#475569",
                ],
                "circle-stroke-color": "#0a0a0a",
                "circle-stroke-width": 0.5,
                "circle-opacity": [
                  "interpolate",
                  ["linear"],
                  ["zoom"],
                  4,
                  0,
                  5,
                  0.8,
                ],
              }}
            />
          </Source>
        )}

        {/* Hover tooltip */}
        {hoverInfo && (
          <Popup
            longitude={hoverInfo.longitude}
            latitude={hoverInfo.latitude}
            closeButton={false}
            closeOnClick={false}
            anchor="bottom"
            offset={8}
          >
            <div className="rounded-md bg-[#171717] px-3 py-2 text-xs">
              <div className="font-semibold text-white">
                {hoverInfo.country}
              </div>
              {hoverInfo.category && (
                <div className="mt-0.5 text-gray-400">
                  {CATEGORY_META[hoverInfo.category as Category]?.label ??
                    hoverInfo.category}
                </div>
              )}
              {hoverInfo.fatalities != null && hoverInfo.fatalities > 0 && (
                <div className="mt-0.5 font-mono font-bold text-red-500">
                  {hoverInfo.fatalities.toLocaleString()} killed
                </div>
              )}
              {hoverInfo.events != null && hoverInfo.events > 0 && (
                <div className="mt-0.5 text-gray-400">
                  {hoverInfo.events.toLocaleString()} events (90d)
                </div>
              )}
            </div>
          </Popup>
        )}
      </Map>

      {/* Event count badge */}
      <div className="absolute left-4 top-4 rounded-md border border-border bg-background/80 px-3 py-2 text-xs backdrop-blur">
        <span className="font-mono text-text-primary">
          {eventCount.toLocaleString()}
        </span>
        <span className="text-text-dim"> events · 90 days</span>
      </div>

      {/* Category filter bar */}
      <div className="absolute bottom-0 left-0 right-0 border-t border-border bg-background/90 backdrop-blur-md">
        <div className="flex items-center gap-2 overflow-x-auto px-4 py-3">
          <button
            onClick={() =>
              setActiveCats((p) =>
                p.size === CATEGORIES.length ? new Set() : new Set(CATEGORIES)
              )
            }
            className="shrink-0 rounded-md border border-border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-text-dim hover:text-text-primary"
          >
            {activeCats.size === CATEGORIES.length ? "Clear" : "All"}
          </button>
          {CATEGORIES.map((cat) => {
            const meta = CATEGORY_META[cat];
            const on = activeCats.has(cat);
            return (
              <button
                key={cat}
                onClick={() =>
                  setActiveCats((p) => {
                    const n = new Set(p);
                    n.has(cat) ? n.delete(cat) : n.add(cat);
                    return n;
                  })
                }
                className={`shrink-0 rounded-md border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider transition ${
                  on
                    ? "border-transparent text-white"
                    : "border-border text-text-dim hover:text-text-primary"
                }`}
                style={on ? { background: meta.color } : undefined}
              >
                {meta.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
