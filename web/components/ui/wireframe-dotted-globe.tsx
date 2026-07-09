"use client";

import { useEffect, useRef, useState } from "react";
import { geoOrthographic, geoPath, geoGraticule, geoDistance, timer } from "d3";

export interface GlobePoint {
  lat: number;
  lng: number;
  /** Relative weight (e.g. fatalities) — drives the dot size. */
  weight?: number;
  /** Marker color (defaults to red). */
  color?: string;
  /** Tooltip label shown on hover. */
  label?: string;
}

interface Props {
  points?: GlobePoint[];
  className?: string;
  /** Rotation speed in degrees/frame. */
  speed?: number;
}

let _landCache: any = null;

type Hover = { x: number; y: number; label: string } | null;

/**
 * Data-driven wireframe globe — a d3 geoOrthographic canvas that renders a faint
 * land outline + graticule and plots real event coordinates as category-colored
 * markers sized by toll, with a hover tooltip. Sizes to its container,
 * auto-rotates (pausing while you inspect a point), drag + wheel-zoom.
 */
export default function WireGlobe({ points = [], className = "", speed = 0.22 }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointsRef = useRef(points);
  pointsRef.current = points;
  // Screen positions of the currently-visible markers, refreshed each frame.
  const screenRef = useRef<{ x: number; y: number; label: string }[]>([]);
  const hoverIndexRef = useRef<number | null>(null);
  const [hover, setHover] = useState<Hover>(null);

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

      ctx.beginPath();
      ctx.arc(size / 2, size / 2, projection.scale(), 0, 2 * Math.PI);
      ctx.fillStyle = "#0b0c0e";
      ctx.fill();
      ctx.strokeStyle = "#2A2E36";
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.beginPath();
      path(graticule);
      ctx.strokeStyle = "rgba(152,160,172,0.10)";
      ctx.lineWidth = 0.6;
      ctx.stroke();

      if (land) {
        ctx.beginPath();
        path(land);
        ctx.strokeStyle = "rgba(200,206,214,0.34)";
        ctx.lineWidth = 0.7;
        ctx.stroke();
      }

      // Markers (front hemisphere only) — glow + core, colored by category.
      const center: [number, number] = [-rotation[0], -rotation[1]];
      const screen: { x: number; y: number; label: string }[] = [];
      const hi = hoverIndexRef.current;
      pointsRef.current.forEach((p, i) => {
        if (geoDistance(center, [p.lng, p.lat]) > Math.PI / 2) return;
        const xy = projection([p.lng, p.lat]);
        if (!xy) return;
        const active = i === hi;
        const col = p.color ?? "#f04747";
        const r = (1.1 + Math.min(4.2, Math.sqrt(p.weight ?? 1) / 3)) * sf * (active ? 1.5 : 1);
        ctx.beginPath();
        ctx.arc(xy[0], xy[1], r * 3, 0, 2 * Math.PI);
        ctx.fillStyle = hexA(col, active ? 0.28 : 0.1);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(xy[0], xy[1], r, 0, 2 * Math.PI);
        ctx.fillStyle = col;
        ctx.fill();
        if (active) {
          ctx.lineWidth = 1;
          ctx.strokeStyle = "#ECEEF1";
          ctx.stroke();
        }
        if (p.label) screen.push({ x: xy[0], y: xy[1], label: p.label });
      });
      screenRef.current = screen;
    };

    resize();
    projection.rotate(rotation);
    render();

    const ro = new ResizeObserver(() => { resize(); render(); });
    ro.observe(wrap);

    if (!land) {
      fetch("/ne_110m_land.json")
        .then((r) => r.json())
        .then((json) => { _landCache = json; land = json; })
        .catch(() => {});
    }

    let dragging = false;
    let auto = true;
    const spin = timer(() => {
      if (auto && !dragging && hoverIndexRef.current === null) {
        rotation[0] += speed;
        projection.rotate(rotation);
      }
      render();
    });

    let startX = 0, startY = 0;
    let startRot: [number, number] = [0, 0];
    const onDown = (e: PointerEvent) => {
      dragging = true;
      startX = e.clientX; startY = e.clientY;
      startRot = [rotation[0], rotation[1]];
      canvas.setPointerCapture(e.pointerId);
    };
    const onMove = (e: PointerEvent) => {
      if (dragging) {
        rotation[0] = startRot[0] + (e.clientX - startX) * 0.4;
        rotation[1] = Math.max(-90, Math.min(90, startRot[1] - (e.clientY - startY) * 0.4));
        projection.rotate(rotation);
        return;
      }
      // Hover hit-test against the visible markers.
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      let best = -1, bestD = 13;
      const scr = screenRef.current;
      for (let i = 0; i < scr.length; i++) {
        const d = Math.hypot(scr[i].x - mx, scr[i].y - my);
        if (d < bestD) { bestD = d; best = i; }
      }
      if (best >= 0) {
        const s = scr[best];
        // Map back to the points index by matching label+pos is overkill; just
        // enlarge the nearest marker and show its tooltip.
        hoverIndexRef.current = indexOfScreen(pointsRef.current, projection, [-rotation[0], -rotation[1]], s);
        setHover({ x: s.x, y: s.y, label: s.label });
      } else if (hoverIndexRef.current !== null) {
        hoverIndexRef.current = null;
        setHover(null);
      }
    };
    const onUp = () => { dragging = false; };
    const onLeave = () => { hoverIndexRef.current = null; setHover(null); };
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const f = e.deltaY > 0 ? 0.92 : 1.08;
      projection.scale(Math.max(radius * 0.7, Math.min(radius * 2.4, projection.scale() * f)));
    };
    canvas.addEventListener("pointerdown", onDown);
    canvas.addEventListener("pointermove", onMove);
    canvas.addEventListener("pointerup", onUp);
    canvas.addEventListener("pointerleave", onLeave);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      spin.stop();
      ro.disconnect();
      canvas.removeEventListener("pointerdown", onDown);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerup", onUp);
      canvas.removeEventListener("pointerleave", onLeave);
      canvas.removeEventListener("wheel", onWheel);
    };
  }, [speed]);

  return (
    <div ref={wrapRef} className={`relative aspect-square w-full ${className}`}>
      <canvas ref={canvasRef} className="h-full w-full cursor-grab touch-none active:cursor-grabbing" />
      {hover && (
        <div
          className="pointer-events-none absolute z-10 max-w-[200px] -translate-x-1/2 -translate-y-full rounded-md border border-border bg-background/95 px-2.5 py-1.5 text-[11px] leading-snug text-text-primary shadow-lg backdrop-blur"
          style={{ left: hover.x, top: hover.y - 10 }}
        >
          {hover.label}
        </div>
      )}
    </div>
  );
}

/** Find which point index the hovered screen marker corresponds to (nearest by projection). */
function indexOfScreen(
  points: GlobePoint[],
  projection: any,
  center: [number, number],
  s: { x: number; y: number },
): number {
  let best = -1, bestD = Infinity;
  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    if (geoDistance(center, [p.lng, p.lat]) > Math.PI / 2) continue;
    const xy = projection([p.lng, p.lat]);
    if (!xy) continue;
    const d = Math.hypot(xy[0] - s.x, xy[1] - s.y);
    if (d < bestD) { bestD = d; best = i; }
  }
  return best;
}

/** "#rrggbb" + alpha → rgba() string. */
function hexA(hex: string, a: number): string {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}
