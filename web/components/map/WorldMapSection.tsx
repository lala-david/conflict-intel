import { getCountryThreatScores } from "@/lib/queries";
import { WorldMapClient } from "./WorldMapClient";

export function WorldMapSection() {
  const countryScores = getCountryThreatScores();

  return (
    <section className="mx-auto max-w-7xl px-6 py-12">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="font-display text-2xl font-bold">Global Threat Map</h2>
        <span className="text-sm text-text-dim">
          Zoom in to see individual events
        </span>
      </div>
      <WorldMapClient countryScores={countryScores} />
    </section>
  );
}
