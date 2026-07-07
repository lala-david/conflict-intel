"""
Wikipedia — "List of terrorist incidents in {year}" (2017-present).

GTD stops at 2016, so recent years are thin. These curated Wikipedia lists cover
the significant attacks 2017→now in a structured table (Date/Type/Dead/Injured/
Location/Details/Perpetrator). Parsed with pandas.read_html; location split into
city + country, dates normalized. category=terrorism.
"""
import re
import time
from io import StringIO

import pandas as pd
import requests

_UA = {"User-Agent": "conflict-intel/1.0 (research)"}
_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}


def _to_date(raw: str, year: int) -> str | None:
    s = re.split(r"[–\-]", str(raw))[0].strip()          # first day of any range
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)", s) or re.search(r"([A-Za-z]+)\s+(\d{1,2})", s)
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    day, mon = (a, b) if a.isdigit() else (b, a)
    mi = _MONTHS.get(mon.lower())
    if not mi:
        return None
    d = min(max(int(day), 1), 28)
    return f"{year:04d}-{mi:02d}-{d:02d}"


def _int(v):
    m = re.search(r"\d[\d,]*", str(v))
    return int(m.group(0).replace(",", "")) if m else 0


def _split_loc(loc: str, countries: set[str]) -> tuple[str, str]:
    """'Kabul, Afghanistan' -> (city, country). Match country from the last parts."""
    loc = re.sub(r"\[.*?\]", "", str(loc)).strip()
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    if not parts:
        return "", ""
    for i in range(len(parts)):                          # last part first
        cand = parts[len(parts) - 1 - i]
        if cand in countries:
            city = ", ".join(parts[: len(parts) - 1 - i])
            return city, cand
    return ", ".join(parts[:-1]), parts[-1]              # fallback: last = country


_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"]


def _tables_for(title: str):
    for attempt in range(3):
        try:
            time.sleep(0.4)                              # be polite → avoid 429
            r = requests.get("https://en.wikipedia.org/w/api.php", timeout=40, headers=_UA,
                             params={"action": "parse", "page": title, "format": "json",
                                     "prop": "text"})
            if r.status_code == 429:
                time.sleep(2 + attempt * 2)
                continue
            j = r.json()
            if "parse" not in j:
                return []
            return pd.read_html(StringIO(j["parse"]["text"]["*"]))
        except Exception:
            time.sleep(1)
    return []


def fetch_wiki_terror(years, countries: set[str] | None = None) -> list[dict]:
    countries = countries or set()
    out: list[dict] = []
    seen: set[str] = set()
    for year in years:
        # yearly article + monthly sub-articles (busy years are split by month)
        titles = [f"List of terrorist incidents in {year}"]
        titles += [f"List of terrorist incidents in {mo} {year}" for mo in _MONTH_NAMES]
        tables = []
        for title in titles:
            tables += _tables_for(title)
        for t in tables:
            cols = [str(c) for c in t.columns]
            if not any("Date" in c for c in cols) or not any("Dead" in c for c in cols):
                continue
            t.columns = cols
            for _, row in t.iterrows():
                date = _to_date(row.get("Date", ""), year)
                if not date:
                    continue
                city, country = _split_loc(row.get("Location", ""), countries)
                perp = re.sub(r"\[.*?\]", "", str(row.get("Perpetrator", ""))).strip()
                if perp.lower() in ("unknown", "nan", "", "unknown perpetrator", "none"):
                    perp = ""
                details = re.sub(r"\[.*?\]|\s+", lambda m: " " if m.group().isspace() else "",
                                 str(row.get("Details", ""))).strip()
                eid = f"wikiterror-{date}-{abs(hash((city, country, perp, details[:40]))) % 10**8}"
                if eid in seen:
                    continue
                seen.add(eid)
                out.append({
                    "id": eid,
                    "source": "wikipedia",
                    "date": date,
                    "event_type": re.sub(r"\[.*?\]", "", str(row.get("Type", ""))).strip()[:40],
                    "actor1": perp[:60],
                    "actor2": "",
                    "country": country,
                    "location": city,
                    "latitude": None,
                    "longitude": None,
                    "fatalities": _int(row.get("Dead", 0)),
                    "notes": details[:500],
                    "category": "terrorism",
                })
    return out


if __name__ == "__main__":
    rows = fetch_wiki_terror(range(2017, 2027))
    print(f"Wikipedia terror parsed: {len(rows):,}")
    by = {}
    for r in rows:
        by[r["date"][:4]] = by.get(r["date"][:4], 0) + 1
    print("  by year:", by)
    print("  sample:", {k: rows[0][k] for k in ("date", "country", "location", "actor1", "fatalities")} if rows else "none")
