import { WorldMapSection } from "@/components/map/WorldMapSection";

export const runtime = "edge";

export const revalidate = 3600;

export default function MapEmbed() {
  return (
    <div
      style={{
        width: "100%",
        height: "100vh",
        background: "#0a0a0a",
        overflow: "hidden",
      }}
    >
      <div style={{ height: "100%" }}>
        <WorldMapSection />
      </div>
    </div>
  );
}
