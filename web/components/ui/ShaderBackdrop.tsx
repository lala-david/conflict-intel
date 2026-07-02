"use client";

import { Warp } from "@paper-design/shaders-react";

/**
 * Subtle, on-brand animated shader used as a hero backdrop.
 * Warm newsprint-dark + signature red — restrained, low opacity,
 * with a gradient fade so foreground text stays legible.
 */
export function ShaderBackdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <Warp
        style={{ height: "100%", width: "100%", opacity: 0.4 }}
        proportion={0.4}
        softness={1.2}
        distortion={0.16}
        swirl={0.65}
        swirlIterations={8}
        shape="checks"
        shapeScale={0.05}
        scale={1.5}
        rotation={0}
        speed={0.22}
        colors={["#0C0D0F", "#15171B", "#EF4444", "#1E2127"]}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-background/50 via-background/70 to-background" />
    </div>
  );
}
