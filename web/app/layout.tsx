import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Conflict Researcher — Daily Global Armed Violence Monitor",
  description:
    "420,000+ events across 37 years. Terrorism, civil war, cartels, insurgency. Categorized by academic standard. Open source.",
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
    title: "Conflict Researcher",
    description:
      "420K events · 37 years · 161 countries · Daily updates · Open source",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Conflict Researcher",
    description:
      "420K events · 37 years · Daily updates · Open source",
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
