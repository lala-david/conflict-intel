import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { WaitlistForm } from "@/components/ui/WaitlistForm";
import { Check, X } from "lucide-react";

export const metadata = {
  title: "Pricing — Conflict & Security Intelligence",
  description: "Free, Pro, and Team plans for conflict intelligence data.",
};

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "For casual monitoring and exploration",
    cta: "Get started",
    ctaHref: "/",
    highlight: false,
    features: [
      { text: "Global dashboard + map", included: true },
      { text: "Top 30 countries detailed", included: true },
      { text: "Top 20 organizations", included: true },
      { text: "Last 90 days events", included: true },
      { text: "Daily brief (Telegram)", included: true },
      { text: "Basic search", included: true },
      { text: "Embed widgets", included: true },
      { text: "API: 100 calls/day", included: true },
      { text: "Full timeline since 1970", included: false },
      { text: "All 250+ countries", included: false },
      { text: "CSV download", included: false },
      { text: "Custom alerts", included: false },
    ],
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    yearlyPrice: "$249/year (save 28%)",
    description: "For analysts, consultants, and researchers",
    cta: "Coming Soon",
    ctaHref: "#notify",
    highlight: true,
    features: [
      { text: "Everything in Free", included: true },
      { text: "All 250+ countries detailed", included: true },
      { text: "All 286 organizations + 341 persons", included: true },
      { text: "Full timeline since 1970", included: true },
      { text: "570K+ events full access", included: true },
      { text: "CSV download per country", included: true },
      { text: "Custom Telegram alerts", included: true },
      { text: "Email Morning Brief", included: true },
      { text: "Weekly Recap", included: true },
      { text: "API: 10K calls/day", included: true },
      { text: 'Remove "Powered by" on widgets', included: true },
      { text: "Priority support", included: false },
    ],
  },
  {
    name: "Team",
    price: "$99",
    period: "/month",
    yearlyPrice: "$899/year (save 25%)",
    description: "For NGOs, security firms, and research teams",
    cta: "Coming Soon",
    ctaHref: "#notify",
    highlight: false,
    features: [
      { text: "Everything in Pro", included: true },
      { text: "5 team members", included: true },
      { text: "Custom dashboard", included: true },
      { text: "API: 100K calls/day", included: true },
      { text: "Slack/Discord webhooks", included: true },
      { text: "Priority support", included: true },
      { text: "Invoice billing", included: true },
      { text: "Data export (full DB)", included: true },
    ],
  },
];

export default function PricingPage() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-6 py-16">
        <div className="text-center">
          <h1 className="font-display text-5xl font-bold">Pricing</h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-text-dim">
            Janes costs $150K/year. We cost $29/month.
            <br />
            Same data depth. Honest classification.
          </p>
        </div>

        <div className="mt-16 grid gap-6 lg:grid-cols-3">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-2xl border p-8 ${
                plan.highlight
                  ? "border-accent bg-surface shadow-lg shadow-accent/10"
                  : "border-border bg-surface"
              }`}
            >
              {plan.highlight && (
                <div className="mb-4 inline-block rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
                  Most Popular
                </div>
              )}
              <h2 className="font-display text-2xl font-bold">{plan.name}</h2>
              <p className="mt-1 text-sm text-text-dim">{plan.description}</p>

              <div className="mt-6 flex items-baseline gap-1">
                <span className="font-display text-5xl font-bold">
                  {plan.price}
                </span>
                <span className="text-text-dim">{plan.period}</span>
              </div>
              {plan.yearlyPrice && (
                <div className="mt-1 text-xs text-text-dim">
                  {plan.yearlyPrice}
                </div>
              )}

              <a
                href={plan.ctaHref}
                className={`mt-6 block w-full rounded-lg py-3 text-center text-sm font-semibold transition ${
                  plan.highlight
                    ? "bg-accent text-white hover:bg-accent/90"
                    : "border border-border text-text-primary hover:bg-surface-2"
                }`}
              >
                {plan.cta}
              </a>

              <ul className="mt-8 space-y-3">
                {plan.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm">
                    {f.included ? (
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-cat-counterterrorism" />
                    ) : (
                      <X className="mt-0.5 h-4 w-4 shrink-0 text-text-dim/40" />
                    )}
                    <span className={f.included ? "text-text-primary" : "text-text-dim/60"}>
                      {f.text}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Notify form */}
        <div id="notify" className="mx-auto mt-20 max-w-lg text-center">
          <h3 className="font-display text-2xl font-bold">
            Get notified when Pro launches
          </h3>
          <p className="mt-2 text-sm text-text-dim">
            We&apos;ll email you once. No spam.
          </p>
          <div className="mt-6 text-left">
            <WaitlistForm interest="pro" cta="Notify me" placeholder="you@company.com" />
          </div>
        </div>

        {/* Enterprise */}
        <div className="mx-auto mt-20 max-w-2xl rounded-xl border border-border bg-surface p-8 text-center">
          <h3 className="font-display text-xl font-bold">Enterprise</h3>
          <p className="mt-2 text-sm text-text-dim">
            Need custom data feeds, SLA, on-premise deployment, or API
            integration for your platform? Let&apos;s talk.
          </p>
          <a
            href="mailto:hello@conflict-researcher.dev"
            className="mt-4 inline-block rounded-lg border border-border px-6 py-2.5 text-sm font-medium text-text-primary hover:bg-surface-2"
          >
            Contact us
          </a>
        </div>

        {/* Comparison */}
        <div className="mx-auto mt-20 max-w-2xl">
          <h3 className="mb-6 text-center font-display text-2xl font-bold">
            How we compare
          </h3>
          <div className="rounded-lg border border-border bg-surface">
            <div className="grid grid-cols-4 gap-4 border-b border-border px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-text-dim">
              <div>Feature</div>
              <div className="text-center">Us (Pro)</div>
              <div className="text-center">ACLED</div>
              <div className="text-center">Janes</div>
            </div>
            {[
              ["Price", "$29/mo", "$10K+/yr", "$150K+/yr"],
              ["Events", "570K+", "~500K", "Classified"],
              ["History", "Since 1970", "1997+", "Unknown"],
              ["Categories", "10 academic", "Custom", "Custom"],
              ["API", "Included", "Extra cost", "Extra cost"],
              ["Open source", "Yes (MIT)", "No", "No"],
              ["Real-time", "Daily", "Weekly", "Real-time"],
              ["Classification", "Honest labels", "Own taxonomy", "Own taxonomy"],
            ].map(([feature, us, acled, janes], i) => (
              <div
                key={i}
                className="grid grid-cols-4 gap-4 border-b border-border px-5 py-3 text-sm last:border-b-0"
              >
                <div className="text-text-dim">{feature}</div>
                <div className="text-center font-medium text-accent">{us}</div>
                <div className="text-center text-text-dim">{acled}</div>
                <div className="text-center text-text-dim">{janes}</div>
              </div>
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
