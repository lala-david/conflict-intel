import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Conflict & Security Intelligence — Track Global Conflict, Daily",
  description:
    "Track the countries, actors and categories you follow across 420,000+ conflict events. One live, categorized feed — updated every morning.",
  keywords: [
    "conflict",
    "terrorism",
    "civil war",
    "insurgency",
    "security",
    "armed violence",
  ],
  authors: [{ name: "David" }],
  openGraph: {
    title: "Conflict & Security Intelligence",
    description:
      "420K events · 38 years · 172 countries · Daily updates",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Conflict & Security Intelligence",
    description:
      "420K events · 38 years · Daily updates",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-text-primary antialiased">
        {children}
      </body>
    </html>
  );
}
