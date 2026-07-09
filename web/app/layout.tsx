import type { Metadata } from "next";
import { SITE_URL } from "@/lib/utils";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Conflict & Security Intelligence — Track Global Conflict, Daily",
  description:
    "Track the countries, actors and categories you follow across 570,000+ conflict events since 1970. One live, categorized feed — updated every morning.",
  keywords: [
    "conflict",
    "terrorism",
    "civil war",
    "insurgency",
    "security",
    "armed violence",
  ],
  authors: [{ name: "David" }],
  alternates: {
    types: {
      "application/rss+xml": [{ url: "/feed.xml", title: "Daily Brief — RSS" }],
    },
  },
  openGraph: {
    title: "Conflict & Security Intelligence",
    description:
      "570K+ events · since 1970 · 250+ countries · Daily updates",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Conflict & Security Intelligence",
    description:
      "570K+ events · since 1970 · Daily updates",
  },
};

const ORG_JSON_LD = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Conflict & Security Intelligence",
  url: SITE_URL,
  description:
    "A live, categorized feed of 570,000+ armed-conflict and security events since 1970, built from UCDP, GTD, GDELT and open-source intelligence.",
  sameAs: [
    "https://t.me/conflictintel",
    "https://github.com/lala-david",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-text-primary antialiased">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(ORG_JSON_LD) }}
        />
        {children}
        {process.env.NEXT_PUBLIC_CF_BEACON_TOKEN && (
          // Cloudflare Web Analytics — privacy-friendly, no cookies. Token from
          // the CF dashboard (Web Analytics → add site), set as NEXT_PUBLIC_CF_BEACON_TOKEN.
          <script
            defer
            src="https://static.cloudflareinsights.com/beacon.min.js"
            data-cf-beacon={`{"token": "${process.env.NEXT_PUBLIC_CF_BEACON_TOKEN}"}`}
          />
        )}
      </body>
    </html>
  );
}
