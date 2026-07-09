/**
 * AI VERIFICATION reviews for events.
 *
 * The offline AI pass (scripts/ai_verify.py) cross-checks the corroborating
 * sources of high-value events with a local LLM and writes a small verification
 * note per event into the `event_reviews` table. This surfaces that note at read
 * time for the event detail page.
 *
 * The table only exists once the AI pass has run and (for D1) been applied/synced,
 * so every read is wrapped in try/catch: a missing table (or any read error) must
 * return null, never 500 the page.
 */
import { queryOne } from "@/lib/db";

export interface EventReview {
  eventId: string;
  /** the AI's proposed reliability grade */
  aiGrade: string | null;
  /** "consistent" | "partial" | "conflicting" */
  consistency: string | null;
  /** "agree" | "dispute" | "single-source" */
  tollAgreement: string | null;
  /** "high" | "medium" | "low" */
  geoConfidence: string | null;
  /** <=280 char note on what the sources agree/disagree on */
  summary: string | null;
  /** local LLM model id that produced the note */
  model: string | null;
  /** ISO timestamp the review was written */
  reviewedAt: string | null;
}

interface ReviewRow {
  event_id: string;
  ai_grade: string | null;
  consistency: string | null;
  toll_agreement: string | null;
  geo_confidence: string | null;
  summary: string | null;
  model: string | null;
  reviewed_at: string | null;
}

/**
 * The AI verification note for one event, or null if none exists / the table is
 * absent. PK lookup, so a single cheap indexed read.
 */
export async function getEventReview(id: string): Promise<EventReview | null> {
  try {
    const row = await queryOne<ReviewRow>(
      `SELECT event_id, ai_grade, consistency, toll_agreement, geo_confidence,
              summary, model, reviewed_at
         FROM event_reviews
        WHERE event_id = ?`,
      [id],
    );
    if (!row) return null;
    return {
      eventId: row.event_id,
      aiGrade: row.ai_grade,
      consistency: row.consistency,
      tollAgreement: row.toll_agreement,
      geoConfidence: row.geo_confidence,
      summary: row.summary,
      model: row.model,
      reviewedAt: row.reviewed_at,
    };
  } catch {
    // Table not yet created (AI pass never run / not synced to D1) — no panel.
    return null;
  }
}
