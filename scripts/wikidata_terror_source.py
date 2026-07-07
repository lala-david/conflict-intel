"""
Wikidata — terrorist attacks (2017-present) via SPARQL.

Complements the Wikipedia lists: structured items with coordinates + death counts
+ perpetrator built in. Instance-of (P31) terrorist attack (Q2223653) or subclass.
"""
import re

import requests

_ENDPOINT = "https://query.wikidata.org/sparql"
_UA = {"User-Agent": "conflict-intel/1.0 (research)",
       "Accept": "application/sparql-results+json"}

_QUERY = """
SELECT ?e ?eLabel ?date ?coord ?deaths ?countryLabel ?locLabel ?perpLabel WHERE {
  ?e wdt:P31/wdt:P279* wd:Q2223653 .
  ?e wdt:P585 ?date .
  FILTER(YEAR(?date) >= %d)
  OPTIONAL { ?e wdt:P625 ?coord }
  OPTIONAL { ?e wdt:P1120 ?deaths }
  OPTIONAL { ?e wdt:P17 ?country }
  OPTIONAL { ?e wdt:P276 ?loc }
  OPTIONAL { ?e wdt:P8031 ?perp }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} LIMIT 10000
"""


def _v(row, key):
    return (row.get(key, {}) or {}).get("value", "") or ""


def fetch_wikidata_terror(since_year: int = 2017) -> list[dict]:
    r = requests.get(_ENDPOINT, params={"query": _QUERY % since_year, "format": "json"},
                     headers=_UA, timeout=90)
    r.raise_for_status()
    out, seen = [], set()
    for row in r.json()["results"]["bindings"]:
        qid = _v(row, "e").rsplit("/", 1)[-1]
        if not qid or qid in seen:
            continue
        seen.add(qid)
        date = _v(row, "date")[:10]
        if not re.match(r"\d{4}-\d{2}-\d{2}", date):
            continue
        lat = lng = None
        m = re.match(r"Point\(([-\d.]+)\s+([-\d.]+)\)", _v(row, "coord"))
        if m:
            lng, lat = float(m.group(1)), float(m.group(2))
        deaths = _v(row, "deaths")
        fat = int(float(deaths)) if deaths.replace(".", "").isdigit() else 0
        label = _v(row, "eLabel")
        if label.startswith("Q") and label[1:].isdigit():
            label = ""
        perp = _v(row, "perpLabel")
        perp = "" if perp.startswith("Q") and perp[1:].isdigit() else perp
        out.append({
            "id": f"wikidata-{qid}",
            "source": "wikidata",
            "date": date,
            "event_type": "",
            "actor1": perp[:60],
            "actor2": "",
            "country": _v(row, "countryLabel"),
            "location": _v(row, "locLabel") or "",
            "latitude": lat,
            "longitude": lng,
            "fatalities": fat,
            "notes": label[:300],
            "category": "terrorism",
        })
    return out


if __name__ == "__main__":
    rows = fetch_wikidata_terror()
    print(f"Wikidata terror: {len(rows):,} | coords {sum(1 for r in rows if r['latitude']):,} | "
          f"deaths {sum(r['fatalities'] for r in rows):,}")
    by = {}
    for r in rows:
        by[r["date"][:4]] = by.get(r["date"][:4], 0) + 1
    print("  by year:", dict(sorted(by.items())))
