"""
GTD — Global Terrorism Database (START/UMD), 1970-2016, ~170k terrorist attacks.

The canonical open terror dataset; our UCDP feed only starts 1989, so this fills
the historical gap. One-time backfill (the file is static). Streamed from a public
GitHub mirror, parsed by column name (robust to column order).
"""
import csv
import os
import tempfile

import requests

GTD_URL = ("https://raw.githubusercontent.com/akashav1/global_terrorist_data/"
           "master/globalterrorismdb_0617dist.csv")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_gtd(timeout: int = 600) -> list[dict]:
    """Download + parse GTD into normalized event dicts (category=terrorism)."""
    resp = requests.get(GTD_URL, timeout=timeout, stream=True)
    resp.raise_for_status()
    fd, path = tempfile.mkstemp(suffix="_gtd.csv")
    with os.fdopen(fd, "wb") as f:
        for chunk in resp.iter_content(1 << 20):
            f.write(chunk)
    out: list[dict] = []
    try:
        with open(path, encoding="latin-1", newline="") as f:
            for i, row in enumerate(csv.DictReader(f)):
                y = row.get("iyear")
                if not y or not y.isdigit():
                    continue
                m = row.get("imonth") or "0"
                d = row.get("iday") or "0"
                mm = int(m) if m.isdigit() and m != "0" else 1
                dd = int(d) if d.isdigit() and d != "0" else 1
                mm = min(max(mm, 1), 12)
                dd = min(max(dd, 1), 28)
                date = f"{int(y):04d}-{mm:02d}-{dd:02d}"
                # GTD 'eventid' is missing in this mirror → use a stable row index
                eid = (row.get("eventid") or "").strip() or str(i)
                gname = (row.get("gname") or "").strip()
                actor1 = "" if gname.lower() in ("", "unknown") else gname
                lat, lng = _num(row.get("latitude")), _num(row.get("longitude"))
                if lat is not None and not (-90 <= lat <= 90):
                    lat = None
                if lng is not None and not (-180 <= lng <= 180):
                    lng = None
                nk = _num(row.get("nkill"))
                fat = int(nk) if nk is not None and nk >= 0 else 0
                loc = ", ".join(
                    x for x in (row.get("city", ""), row.get("provstate", ""))
                    if x and x.strip().lower() not in ("", "unknown"))
                out.append({
                    "id": f"gtd-{eid}",
                    "source": "gtd",
                    "date": date,
                    "event_type": (row.get("attacktype1_txt") or "").strip(),
                    "actor1": actor1,
                    "actor2": (row.get("target1") or row.get("targtype1_txt") or "").strip()[:60],
                    "country": (row.get("country_txt") or "").strip(),
                    "location": loc,
                    "latitude": lat,
                    "longitude": lng,
                    "fatalities": fat,
                    "notes": (row.get("summary") or "").strip(),
                    "category": "terrorism",
                })
    finally:
        os.remove(path)
    return out


if __name__ == "__main__":
    rows = fetch_gtd()
    print(f"GTD parsed: {len(rows):,} events")
    yrs = sorted({r["date"][:4] for r in rows})
    print(f"  years: {yrs[0]}–{yrs[-1]} | with coords: {sum(1 for r in rows if r['latitude']):,}")
