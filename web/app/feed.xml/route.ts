/**
 * RSS 2.0 feed of the latest Daily Briefs — enables syndication to
 * Feedly / readers / bots / email-digest services.
 *
 * Absolute links use SITE_URL (single source of truth). Brief metadata comes
 * from the bundled manifest via listBriefs() — no runtime filesystem / API.
 */
import { listBriefs } from "@/lib/briefs";
import { SITE_URL } from "@/lib/utils";

export const revalidate = 3600;

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/** YYYY-MM-DD -> RFC-822 date, pinned to the 06:00 UTC publish slot. */
function pubDate(date: string): string {
  return new Date(`${date}T06:00:00Z`).toUTCString();
}

export async function GET() {
  const briefs = await listBriefs(50);
  const self = `${SITE_URL}/feed.xml`;
  const built = new Date().toUTCString();

  const items = briefs
    .map((b) => {
      const link = `${SITE_URL}/brief/${b.date}`;
      const title = `Daily Brief — ${b.date}`;
      const description =
        `Intelligence brief for ${b.date}: threat-level assessment, ` +
        `conflict events, organized-violence hotspots, and cross-source news clusters.`;
      return [
        "    <item>",
        `      <title>${esc(title)}</title>`,
        `      <link>${esc(link)}</link>`,
        `      <guid isPermaLink="true">${esc(link)}</guid>`,
        `      <pubDate>${pubDate(b.date)}</pubDate>`,
        `      <description>${esc(description)}</description>`,
        "    </item>",
      ].join("\n");
    })
    .join("\n");

  const xml =
    `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n` +
    `  <channel>\n` +
    `    <title>Conflict &amp; Security Intelligence — Daily Brief</title>\n` +
    `    <link>${SITE_URL}/brief</link>\n` +
    `    <atom:link href="${self}" rel="self" type="application/rss+xml" />\n` +
    `    <description>A structured daily intelligence read of the world's organized violence — auto-generated every morning.</description>\n` +
    `    <language>en</language>\n` +
    `    <lastBuildDate>${built}</lastBuildDate>\n` +
    `${items}\n` +
    `  </channel>\n` +
    `</rss>\n`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600, s-maxage=3600",
    },
  });
}
