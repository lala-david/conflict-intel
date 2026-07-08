/**
 * Shared TypeScript types for the Conflict & Security Intelligence dashboard.
 */

export type Category =
  | "war"
  | "civil_war"
  | "terrorism"
  | "mass_atrocity"
  | "state_violence"
  | "cartel_violence"
  | "communal_violence"
  | "insurgency"
  | "counterterrorism"
  | "armed_violence";

export type Confidence = "high" | "medium" | "low";

export interface Event {
  id: string;
  source: string;
  date: string;
  event_type: string | null;
  actor1: string | null;
  actor2: string | null;
  country: string | null;
  country_code: string | null;
  admin1: string | null;
  location: string | null;
  latitude: number | null;
  longitude: number | null;
  fatalities: number;
  deaths_civilians: number | null;
  fatalities_low: number | null;
  fatalities_high: number | null;
  category: Category | null;
  category_confidence: Confidence | null;
  is_aggregate: number;
  notes: string | null;
  source_url: string | null;
  collected_at?: string | null;
}

/** A geolocated event plotted on a spread map — each point links back to its event. */
export interface SpreadPoint {
  id: string;
  longitude: number;
  latitude: number;
  fatalities: number;
  date: string;
  category: Category | null;
  country: string | null;
  location: string | null;
  actor1: string | null;
  actor2: string | null;
}

export interface Country {
  country: string;
  event_count: number;
  total_fatalities: number;
  recent_30d_events: number;
  recent_30d_fatalities: number;
}

export interface Organization {
  name: string;
  event_count: number;
  total_fatalities: number;
  countries: string[];
  first_seen: string;
  last_seen: string;
}

export interface CategoryStats {
  category: Category;
  events: number;
  fatalities: number;
}

export interface HotRegion {
  country: string;
  events: number;
  fatalities: number;
}

export interface ThreatIndex {
  value: number;
  delta: number;
  trend7d: number[];
}

export interface HomeData {
  threatIndex: ThreatIndex;
  totals: {
    events: number;
    fatalities: number;
    countries: number;
  };
  categories: Record<Category, { events: number; fatalities: number }>;
  hotRegions: HotRegion[];
  recentEvents: Event[];
}

export interface CryptoWallet {
  address: string;
  chain: string;
  entity_name: string;
  is_terror: number;
  org: string | null;
  category: string;
  topics: string;
  source: string;
}
