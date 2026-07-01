import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Conflict & Security Intelligence — Daily Global Armed Violence Monitor",
  description:
    "420,000+ events across 38 years. Civil war, insurgency, terrorism, cartels, and more. Categorized by academic standard. Open source.",
  keywords: [
    "conflict",
    "terrorism",
    "civil war",
    "OSINT",
    "UCDP",
    "GDELT",
    "armed violence",
  ],
  authors: [{ name: "David" }],
  openGraph: {
    title: "Conflict & Security Intelligence",
    description:
      "420K events · 38 years · 172 countries · Daily updates · Open source",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Conflict & Security Intelligence",
    description:
      "420K events · 38 years · Daily updates · Open source",
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
