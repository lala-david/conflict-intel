import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { SITE_URL } from "@/lib/utils";

export const metadata = {
  title: "Embed Widgets — Conflict & Security Intelligence",
  description: "Free embeddable widgets for country risk, live feed, and threat map.",
};

const WIDGETS = [
  {
    title: "Country Risk Badge",
    description: "Compact 300×100 badge showing current threat level for a country. Updates daily.",
    url: "/embed/badge/Nigeria",
    width: 300,
    height: 100,
    code: `<iframe src="${SITE_URL}/embed/badge/Nigeria"
  width="300" height="100" frameborder="0"></iframe>`,
  },
  {
    title: "Live Threat Feed",
    description: "Auto-refreshing feed of recent events (400×420). Shows category, date, location, fatalities.",
    url: "/embed/feed",
    width: 400,
    height: 420,
    code: `<iframe src="${SITE_URL}/embed/feed"
  width="400" height="420" frameborder="0"></iframe>`,
  },
  {
    title: "Mini Threat Map",
    description: "Responsive world heatmap of last 90 days of events. Interactive tooltips.",
    url: "/embed/map",
    width: 600,
    height: 360,
    code: `<iframe src="${SITE_URL}/embed/map"
  width="100%" height="360" frameborder="0"></iframe>`,
  },
];

export default function WidgetsPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-12">
        <h1 className="font-display text-5xl font-bold">Embed Widgets</h1>
        <p className="mt-2 text-text-dim">
          Free embeddable widgets. No API key, no tracking. Attribution via "Powered by" footer.
        </p>

        <div className="mt-12 space-y-16">
          {WIDGETS.map((w) => (
            <section key={w.title}>
              <h2 className="font-display text-2xl font-bold">{w.title}</h2>
              <p className="mt-2 text-sm text-text-dim">{w.description}</p>

              <div className="mt-5 overflow-hidden rounded-lg border border-border bg-surface p-5">
                <iframe
                  src={w.url}
                  width={w.width}
                  height={w.height}
                  style={{ border: "none", display: "block", margin: "0 auto" }}
                />
              </div>

              <div className="mt-4">
                <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-text-dim">
                  Embed code
                </div>
                <pre className="overflow-x-auto rounded-lg border border-border bg-background p-4 font-mono text-xs text-accent">
                  {w.code}
                </pre>
              </div>
            </section>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
