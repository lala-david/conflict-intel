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
  theta: 0.25,
  dark: 1,
  diffuse: 1.1,
  mapSamples: 16000,
  mapBrightness: 3,
  baseColor: [0.18, 0.19, 0.22],
  markerColor: [239 / 255, 68 / 255, 68 / 255],
  glowColor: [0.35, 0.12, 0.12],
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
    state.width = widthRef.current * 2;
    state.height = widthRef.current * 2;
  }, []);

  useEffect(() => {
    const onResize = () => {
      if (canvasRef.current) widthRef.current = canvasRef.current.offsetWidth;
    };
    window.addEventListener("resize", onResize);
    onResize();
    const opts = {
      ...CONFIG,
      width: widthRef.current * 2,
      height: widthRef.current * 2,
      onRender,
    };
    const globe = createGlobe(canvasRef.current!, opts as COBEOptions);
    setTimeout(() => {
      if (canvasRef.current) canvasRef.current.style.opacity = "1";
    });
    return () => {
      globe.destroy();
      window.removeEventListener("resize", onResize);
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
