"""
Geocoding for events that arrive without coordinates (news / RSS / Telegram /
Wikipedia / OFAC). UCDP and GDELT already carry lat/lon; text sources don't.

Uses OpenStreetMap Nominatim (free, no key) with an on-disk cache so each unique
place is looked up once, and a country-centroid fallback so every event with a
country gets at least coarse coordinates. Respect OSM's 1 req/s policy via a
small sleep on cache misses only.
"""
import json
import time
from pathlib import Path

import requests

_CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / ".geocode_cache.json"
_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_UA = {"User-Agent": "conflict-intel/1.0 (conflict research; contact via github.com/lala-david)"}
_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            _cache = {}
    return _cache


def _save() -> None:
    if _cache is not None:
        try:
            _CACHE_PATH.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


def _query(q: str, sleep: float) -> tuple[float, float] | None:
    try:
        time.sleep(sleep)  # OSM rate limit (cache misses only)
        r = requests.get(_NOMINATIM, params={"q": q, "format": "json", "limit": 1},
                         headers=_UA, timeout=15)
        d = r.json()
        if d:
            return round(float(d[0]["lat"]), 5), round(float(d[0]["lon"]), 5)
    except Exception:
        pass
    return None


def geocode(location: str | None, country: str | None, sleep: float = 1.0) -> tuple[float | None, float | None]:
    """Best-effort (lat, lon) for a place. Tries 'location, country' then the
    country centroid. Results (including misses) are cached."""
    loc = (location or "").strip()
    ctry = (country or "").strip()
    if not loc and not ctry:
        return None, None
    cache = _load()
    key = f"{loc}|{ctry}".lower()
    if key in cache:
        v = cache[key]
        return (v[0], v[1]) if v else (None, None)

    hit = None
    if loc and ctry:
        hit = _query(f"{loc}, {ctry}", sleep)
    elif loc:
        hit = _query(loc, sleep)
    if hit is None and ctry:                      # country-centroid fallback
        ckey = f"|{ctry}".lower()
        if ckey in cache and cache[ckey]:
            hit = tuple(cache[ckey])
        else:
            hit = _query(ctry, sleep)
            cache[ckey] = list(hit) if hit else None

    cache[key] = list(hit) if hit else None
    _save()
    return (hit[0], hit[1]) if hit else (None, None)


def enrich_missing_coords(data: dict, sleep: float = 1.0, max_new: int = 200) -> int:
    """Fill latitude/longitude for event-source rows that lack them. Mutates the
    events in-place; returns how many were newly geocoded. Caps *uncached* network
    lookups at `max_new` per run so a burst of new places can't stall the pipeline
    (cached places are always applied; the rest resolve on the next run)."""
    cache = _load()
    new_lookups = 0
    filled = 0
    for key, events in data.items():
        if key.startswith("_") or not isinstance(events, list):
            continue
        for e in events:
            if not isinstance(e, dict):
                continue
            lat, lon = e.get("latitude"), e.get("longitude")
            try:
                if lat not in (None, "", 0, "0") and lon not in (None, "", 0, "0") \
                        and float(lat) != 0 and float(lon) != 0:
                    continue
            except (TypeError, ValueError):
                pass
            ckey = f"{(e.get('location') or '').strip()}|{(e.get('country') or '').strip()}".lower()
            if ckey not in cache:
                if new_lookups >= max_new:
                    continue  # network budget spent — leave for the next run
                new_lookups += 1
            glat, glon = geocode(e.get("location"), e.get("country"), sleep)
            if glat is not None:
                e["latitude"], e["longitude"] = glat, glon
                filled += 1
    return filled


if __name__ == "__main__":
    for loc, ctry in [("Raqqa", "Syria"), ("", "Nigeria"), ("Kabul", "Afghanistan")]:
        print(f"  {loc or '(country)'}, {ctry} → {geocode(loc, ctry)}")
