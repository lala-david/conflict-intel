"use client";

import { useEffect, useRef } from "react";
import { geoOrthographic, geoPath, geoGraticule, geoDistance, timer } from "d3";

export interface GlobePoint {
  lat: number;
  lng: number;
  /** Relative weight (e.g. fatalities) — drives the dot size. */
  weight?: number;
}

interface Props {
  /** Real coordinates to plot as glowing red markers. */
  points?: GlobePoint[];
  className?: string;
  /** Rotation speed in degrees/frame. */
  speed?: number;
}

let _landCache: any = null;

/**
 * Data-driven wireframe globe — a d3 geoOrthographic canvas that renders a faint
 * land outline + graticule and plots real event coordinates as red markers sized
 * by toll. Sizes to its container (not the window), auto-rotates, drag + zoom.
 */
export default function WireGlobe({ points = [], className = "", speed = 0.22 }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointsRef = useRef(points);
  pointsRef.current = points;

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let size = 0;
    let radius = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const projection = geoOrthographic().clipAngle(90);
    const path = geoPath(projection, ctx);
    const graticule = geoGraticule()();
    const rotation: [number, number] = [-20, -12];
    let land: any = _landCache;

    const resize = () => {
      size = Math.max(120, wrap.clientWidth);
      radius = size / 2.15;
      canvas.width = size * dpr;
      canvas.height = size * dpr;
      canvas.style.width = `${size}px`;
      canvas.style.height = `${size}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      projection.scale(radius).translate([size / 2, size / 2]);
    };

    const render = () => {
      if (!size) return;
      const sf = projection.scale() / radius;
      ctx.clearRect(0, 0, size, size);

      // Sphere
      ctx.beginPath();
      ctx.arc(size / 2, size / 2, projection.scale(), 0, 2 * Math.PI);
      ctx.fillStyle = "#0b0c0e";
      ctx.fill();
      ctx.strokeStyle = "#2A2E36";
      ctx.lineWidth = 1;
      ctx.stroke();

      // Graticule
      ctx.beginPath();
      path(graticule);
      ctx.strokeStyle = "rgba(152,160,172,0.10)";
      ctx.lineWidth = 0.6;
      ctx.stroke();

      // Land outline
      if (land) {
        ctx.beginPath();
        path(land);
        ctx.strokeStyle = "rgba(200,206,214,0.34)";
        ctx.lineWidth = 0.7;
        ctx.stroke();
      }

      // Event markers (front hemisphere only), glow + core
      const center: [number, number] = [-rotation[0], -rotation[1]];
      for (const p of pointsRef.current) {
        if (geoDistance(center, [p.lng, p.lat]) > Math.PI / 2) continue;
        const xy = projection([p.lng, p.lat]);
        if (!xy) continue;
        const r = (1.1 + Math.min(4.2, Math.sqrt(p.weight ?? 1) / 3)) * sf;
        ctx.beginPath();
        ctx.arc(xy[0], xy[1], r * 3, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(239,68,68,0.10)";
        ctx.fill();
        ctx.beginPath();
        ctx.arc(xy[0], xy[1], r, 0, 2 * Math.PI);
        ctx.fillStyle = "#f04747";
        ctx.fill();
      }
    };

    resize();
    projection.rotate(rotation);
    render();

    const ro = new ResizeObserver(() => {
      resize();
      render();
    });
    ro.observe(wrap);

    // Load land once (cached across mounts), then keep rendering.
    if (!land) {
      fetch("/ne_110m_land.json")
        .then((r) => r.json())
        .then((json) => {
          _landCache = json;
          land = json;
        })
        .catch(() => {});
    }

    let dragging = false;
    let auto = true;
    const spin = timer(() => {
      if (auto && !dragging) {
        rotation[0] += speed;
        projection.rotate(rotation);
      }
      render();
    });

    let startX = 0;
    let startY = 0;
    let startRot: [number, number] = [0, 0];
    const onDown = (e: PointerEvent) => {
      dragging = true;
      auto = false;
      startX = e.clientX;
      startY = e.clientY;
      startRot = [rotation[0], rotation[1]];
      canvas.setPointerCapture(e.pointerId);
    };
    const onMove = (e: PointerEvent) => {
      if (!dragging) return;
      rotation[0] = startRot[0] + (e.clientX - startX) * 0.4;
      rotation[1] = Math.max(-90, Math.min(90, startRot[1] - (e.clientY - startY) * 0.4));
      projection.rotate(rotation);
    };
    const onUp = () => {
      dragging = false;
      setTimeout(() => { auto = true; }, 1200);
    };
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const f = e.deltaY > 0 ? 0.92 : 1.08;
      projection.scale(Math.max(radius * 0.7, Math.min(radius * 2.4, projection.scale() * f)));
    };
    canvas.addEventListener("pointerdown", onDown);
    canvas.addEventListener("pointermove", onMove);
    canvas.addEventListener("pointerup", onUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      spin.stop();
      ro.disconnect();
      canvas.removeEventListener("pointerdown", onDown);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerup", onUp);
      canvas.removeEventListener("wheel", onWheel);
    };
  }, [speed]);

  return (
    <div ref={wrapRef} className={`relative aspect-square w-full ${className}`}>
      <canvas ref={canvasRef} className="h-full w-full cursor-grab touch-none active:cursor-grabbing" />
    </div>
  );
}
