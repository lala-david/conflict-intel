import type { MetadataRoute } from "next";
import { getCountryList, getTopOrganizations } from "@/lib/queries";
import { getSitemapEventIds } from "@/lib/queries-sitemap";
import { slugify, SITE_URL } from "@/lib/utils";

export const dynamic = "force-dynamic";

const BASE = SITE_URL;

const CATEGORIES = [
  "war",
  "civil-war",
  "terrorism",
  "mass-atrocity",
  "state-violence",
  "cartel-violence",
  "communal-violence",
  "insurgency",
  "counterterrorism",
  "armed-violence",
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE, lastModified: now, priority: 1.0 },
    { url: `${BASE}/events`, lastModified: now, priority: 0.9 },
    { url: `${BASE}/countries`, lastModified: now, priority: 0.9 },
    { url: `${BASE}/organizations`, lastModified: now, priority: 0.9 },
    { url: `${BASE}/categories`, lastModified: now, priority: 0.8 },
    { url: `${BASE}/brief`, lastModified: now, priority: 0.8 },
    { url: `${BASE}/weekly`, lastModified: now, priority: 0.7 },
    { url: `${BASE}/search`, lastModified: now, priority: 0.7 },
    { url: `${BASE}/widgets`, lastModified: now, priority: 0.6 },
    { url: `${BASE}/pricing`, lastModified: now, priority: 0.5 },
    { url: `${BASE}/about`, lastModified: now, priority: 0.5 },
    { url: `${BASE}/about/methodology`, lastModified: now, priority: 0.5 },
    { url: `${BASE}/api-docs`, lastModified: now, priority: 0.6 },
    { url: `${BASE}/data`, lastModified: now, priority: 0.6 },
  ];

  const categoryPages: MetadataRoute.Sitemap = CATEGORIES.map((cat) => ({
    url: `${BASE}/categories/${cat}`,
    lastModified: now,
    priority: 0.7,
  }));

  const countries = await getCountryList();
  const countryPages: MetadataRoute.Sitemap = countries.map((c) => ({
    url: `${BASE}/countries/${encodeURIComponent(c.country)}`,
    lastModified: now,
    priority: 0.7,
  }));

  const orgs = await getTopOrganizations(100);
  const orgPages: MetadataRoute.Sitemap = orgs.map((o) => ({
    url: `${BASE}/organizations/${slugify(o.name)}`,
    lastModified: now,
    priority: 0.6,
  }));

  // Top server-rendered event pages (breaking-news long-tail). Bounded + cached
  // by the query so this stays fast and can't blow the sitemap size budget.
  const events = await getSitemapEventIds();
  const eventPages: MetadataRoute.Sitemap = events.map((e) => {
    const d = e.date ? new Date(e.date) : now;
    return {
      url: `${BASE}/events/${encodeURIComponent(e.id)}`,
      lastModified: isNaN(d.getTime()) ? now : d,
      priority: 0.5,
    };
  });

  return [
    ...staticPages,
    ...categoryPages,
    ...countryPages,
    ...orgPages,
    ...eventPages,
  ];
}
