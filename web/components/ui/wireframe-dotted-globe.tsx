"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

interface RotatingEarthProps {
  width?: number;
  height?: number;
  className?: string;
  /** Halftone land dot spacing — larger = fewer dots (lighter render). Default 16. */
  dotSpacing?: number;
  /** Land dot + wireframe color. Defaults to a light neutral. */
  landColor?: string;
  dotColor?: string;
}

export default function RotatingEarth({
  width = 800,
  height = 600,
  className = "",
  dotSpacing = 16,
  landColor = "#ECEEF1",
  dotColor = "#8892a0",
}: RotatingEarthProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const context = canvas.getContext("2d");
    if (!context) return;

    const containerWidth = Math.min(width, window.innerWidth - 40);
    const containerHeight = Math.min(height, window.innerHeight - 100);
    const radius = Math.min(containerWidth, containerHeight) / 2.2;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = containerWidth * dpr;
    canvas.height = containerHeight * dpr;
    canvas.style.width = `${containerWidth}px`;
    canvas.style.height = `${containerHeight}px`;
    context.scale(dpr, dpr);

    const projection = d3
      .geoOrthographic()
      .scale(radius)
      .translate([containerWidth / 2, containerHeight / 2])
      .clipAngle(90);

    const path = d3.geoPath().projection(projection).context(context);

    const pointInPolygon = (point: [number, number], polygon: number[][]): boolean => {
      const [x, y] = point;
      let inside = false;
      for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const [xi, yi] = polygon[i];
        const [xj, yj] = polygon[j];
        if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
      }
      return inside;
    };

    const pointInFeature = (point: [number, number], feature: any): boolean => {
      const g = feature.geometry;
      if (g.type === "Polygon") {
        if (!pointInPolygon(point, g.coordinates[0])) return false;
        for (let i = 1; i < g.coordinates.length; i++) {
          if (pointInPolygon(point, g.coordinates[i])) return false;
        }
        return true;
      }
      if (g.type === "MultiPolygon") {
        for (const polygon of g.coordinates) {
          if (pointInPolygon(point, polygon[0])) {
            let inHole = false;
            for (let i = 1; i < polygon.length; i++) {
              if (pointInPolygon(point, polygon[i])) { inHole = true; break; }
            }
            if (!inHole) return true;
          }
        }
      }
      return false;
    };

    const generateDotsInPolygon = (feature: any, spacing: number) => {
      const dots: [number, number][] = [];
      const [[minLng, minLat], [maxLng, maxLat]] = d3.geoBounds(feature);
      const step = spacing * 0.08;
      for (let lng = minLng; lng <= maxLng; lng += step) {
        for (let lat = minLat; lat <= maxLat; lat += step) {
          const p: [number, number] = [lng, lat];
          if (pointInFeature(p, feature)) dots.push(p);
        }
      }
      return dots;
    };

    const allDots: { lng: number; lat: number }[] = [];
    let landFeatures: any;

    const render = () => {
      context.clearRect(0, 0, containerWidth, containerHeight);
      const currentScale = projection.scale();
      const scaleFactor = currentScale / radius;

      // Globe sphere
      context.beginPath();
      context.arc(containerWidth / 2, containerHeight / 2, currentScale, 0, 2 * Math.PI);
      context.fillStyle = "#0C0D0F";
      context.fill();
      context.strokeStyle = landColor;
      context.lineWidth = 1.5 * scaleFactor;
      context.globalAlpha = 0.5;
      context.stroke();
      context.globalAlpha = 1;

      if (landFeatures) {
        // Graticule
        const graticule = d3.geoGraticule();
        context.beginPath();
        path(graticule());
        context.strokeStyle = landColor;
        context.lineWidth = 1 * scaleFactor;
        context.globalAlpha = 0.12;
        context.stroke();
        context.globalAlpha = 1;

        // Land outlines
        context.beginPath();
        landFeatures.features.forEach((f: any) => path(f));
        context.strokeStyle = landColor;
        context.lineWidth = 1 * scaleFactor;
        context.globalAlpha = 0.55;
        context.stroke();
        context.globalAlpha = 1;

        // Halftone dots
        allDots.forEach((dot) => {
          const pj = projection([dot.lng, dot.lat]);
          if (pj && pj[0] >= 0 && pj[0] <= containerWidth && pj[1] >= 0 && pj[1] <= containerHeight) {
            context.beginPath();
            context.arc(pj[0], pj[1], 1.1 * scaleFactor, 0, 2 * Math.PI);
            context.fillStyle = dotColor;
            context.fill();
          }
        });
      }
    };

    const loadWorldData = async () => {
      try {
        const res = await fetch("/ne_110m_land.json");
        if (!res.ok) throw new Error("Failed to load land data");
        landFeatures = await res.json();
        landFeatures.features.forEach((f: any) => {
          generateDotsInPolygon(f, dotSpacing).forEach(([lng, lat]) => allDots.push({ lng, lat }));
        });
        render();
      } catch {
        setError("Failed to load globe");
      }
    };

    const rotation: [number, number] = [0, -12];
    let autoRotate = true;
    const rotate = () => {
      if (autoRotate) {
        rotation[0] += 0.32;
        projection.rotate(rotation);
        render();
      }
    };
    const rotationTimer = d3.timer(rotate);

    const handleMouseDown = (event: MouseEvent) => {
      autoRotate = false;
      const startX = event.clientX;
      const startY = event.clientY;
      const start: [number, number] = [rotation[0], rotation[1]];
      const onMove = (m: MouseEvent) => {
        rotation[0] = start[0] + (m.clientX - startX) * 0.5;
        rotation[1] = Math.max(-90, Math.min(90, start[1] - (m.clientY - startY) * 0.5));
        projection.rotate(rotation);
        render();
      };
      const onUp = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        setTimeout(() => { autoRotate = true; }, 10);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    };

    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      const f = event.deltaY > 0 ? 0.9 : 1.1;
      projection.scale(Math.max(radius * 0.5, Math.min(radius * 3, projection.scale() * f)));
      render();
    };

    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("wheel", handleWheel, { passive: false });
    loadWorldData();

    return () => {
      rotationTimer.stop();
      canvas.removeEventListener("mousedown", handleMouseDown);
      canvas.removeEventListener("wheel", handleWheel);
    };
  }, [width, height, dotSpacing, landColor, dotColor]);

  if (error) {
    return (
      <div className={`flex items-center justify-center rounded-2xl bg-surface p-8 ${className}`}>
        <p className="text-sm text-text-dim">{error}</p>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <canvas
        ref={canvasRef}
        className="h-auto w-full cursor-grab active:cursor-grabbing"
        style={{ maxWidth: "100%", height: "auto" }}
      />
    </div>
  );
}
