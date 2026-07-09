"use client";

import createGlobe, { COBEOptions } from "cobe";
import { useCallback, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

// Terror-finance hotspots — red markers on a dark globe.
const CONFIG: Omit<COBEOptions, "onRender"> = {
  width: 800,
  height: 800,
  devicePixelRatio: 2,
  phi: 0,
  theta: 0.28,
  dark: 0,
  diffuse: 1.2,
  mapSamples: 18000,
  mapBrightness: 6,
  baseColor: [0.52, 0.55, 0.62],
  markerColor: [0.94, 0.13, 0.13],
  glowColor: [0.95, 0.55, 0.55],
  markers: [
    { location: [31.5, 34.47], size: 0.11 },   // Gaza — Hamas
    { location: [33.89, 35.5], size: 0.08 },    // Beirut — Hezbollah
    { location: [35.95, 39.0], size: 0.09 },    // Raqqa — ISIS
    { location: [15.37, 44.19], size: 0.07 },   // Sana'a — Houthis
    { location: [34.53, 69.17], size: 0.08 },   // Kabul — ISIS-K
    { location: [2.04, 45.34], size: 0.06 },    // Mogadishu — al-Shabaab
    { location: [11.83, 13.15], size: 0.06 },   // Maiduguri — Boko Haram
    { location: [33.31, 44.36], size: 0.05 },   // Baghdad
    { location: [30.04, 31.24], size: 0.05 },   // Cairo
    { location: [24.71, 46.68], size: 0.04 },   // Riyadh
    { location: [35.69, 51.39], size: 0.05 },   // Tehran
  ],
};

export function ThreatGlobe({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const phiRef = useRef(0);
  const widthRef = useRef(0);

  const onRender = useCallback((state: Record<string, number>) => {
    phiRef.current += 0.0035;
    state.phi = phiRef.current;
    const w = (widthRef.current || 500) * 2;
    state.width = w;
    state.height = w;
  }, []);

  useEffect(() => {
    const measure = () => {
      if (canvasRef.current) widthRef.current = canvasRef.current.offsetWidth;
    };
    // ResizeObserver (not just window 'resize') so we catch the initial layout
    // settling — offsetWidth is often 0 at mount, which left the globe invisible.
    const ro = new ResizeObserver(measure);
    if (canvasRef.current) ro.observe(canvasRef.current);
    measure();
    // Fallback size so createGlobe never inits at 0; onRender then tracks widthRef.
    const seed = (widthRef.current || 500) * 2;
    const globe = createGlobe(canvasRef.current!, {
      ...CONFIG,
      width: seed,
      height: seed,
      onRender,
    } as COBEOptions);
    setTimeout(() => {
      if (canvasRef.current) canvasRef.current.style.opacity = "1";
    });
    return () => {
      globe.destroy();
      ro.disconnect();
    };
  }, [onRender]);

  return (
    <div className={cn("aspect-square w-full max-w-[520px]", className)}>
      <canvas
        ref={canvasRef}
        className="h-full w-full opacity-0 transition-opacity duration-700 [contain:layout_paint_size]"
      />
    </div>
  );
}
