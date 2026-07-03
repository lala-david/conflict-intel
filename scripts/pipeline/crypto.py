"""
Crypto threat-finance — its own medallion pipeline (Bronze → Silver → Gold).

BRONZE  each open source (OpenSanctions / GraphSense / Ransomwhere) → raw Parquet
        (immutable) + health.
SILVER  merge → dedupe by address → keep threat-actor categories → link to a
        canonical conflict organization → crypto_addresses.
GOLD    serving aggregates → crypto_stats.

Same shape as the events medallion, so the whole product is uniform.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import bronze, health  # noqa: E402
from pipeline.base import ExtractResult  # noqa: E402
from crypto_source import (  # noqa: E402
    fetch_opensanctions, fetch_graphsense, fetch_ransomwhere,
)
from database import init_db, get_conn  # noqa: E402

# Bronze sources (name → extractor)
SOURCES = {
    "crypto_opensanctions": fetch_opensanctions,
    "crypto_graphsense": fetch_graphsense,
    "crypto_ransomwhere": fetch_ransomwhere,
}

# Threat-actor / threat-finance categories surfaced in the product.
PRODUCT_CATEGORIES = {"terror", "sanction", "extremism", "ransomware", "mixer", "hack", "scam"}

# Curated, high-precision holder-name → canonical organization map.
_ORG_ALIASES: list[tuple[tuple[str, ...], str]] = [
    (("isil", "isis", "islamic state", "daesh", "khorasan", "iswap"), "Islamic State"),
    (("hamas", "al-qassam", "qassam", "izz al-din", "izz ad-din", "gaza now", "buy cash"), "Hamas"),
    (("hizballah", "hezbollah"), "Hezbollah"),
    (("ansarallah", "ansar allah", "houthi"), "Houthis (Ansarallah)"),
    (("al-qaida", "al-qaeda", "al qaeda", "alqaeda", "aqap", "aqim", "qaeda"), "al-Qaeda"),
    (("al-shabaab", "al shabaab", "shabaab"), "al-Shabaab"),
    (("palestinian islamic jihad", "islamic jihad", "pij"), "Palestinian Islamic Jihad"),
    (("hayat tahrir", "al-nusra", "nusra"), "Hayat Tahrir al-Sham"),
    (("irgc", "quds force", "quds"), "IRGC / Quds Force"),
    (("boko haram",), "Boko Haram"),
    (("taliban", "haqqani"), "Taliban / Haqqani"),
    (("wagner",), "Wagner Group"),
    (("pkk", "kurdistan workers"), "PKK"),
    (("tehrik-i-taliban", "ttp"), "Tehrik-i-Taliban Pakistan"),
]


def _link_org(entity_name: str, topics: str) -> str | None:
    blob = f"{entity_name} {topics}".lower()
    for keys, canon in _ORG_ALIASES:
        if any(k in blob for k in keys):
            return canon
    return None


def _dedupe(rows: list[dict]) -> list[dict]:
    """Exact-address dedupe (addresses are exact strings — no fuzzy match needed).
    A terror-attributed record wins over a generic one for the same address."""
    by_addr: dict[str, dict] = {}
    for r in rows:
        a = (r.get("address") or "").strip()
        if not a or len(a) < 8:
            continue
        prev = by_addr.get(a)
        if prev is None or (r.get("is_terror") and not prev.get("is_terror")):
            by_addr[a] = r
    return list(by_addr.values())


def run(run_id: str) -> None:
    init_db()

    # ── BRONZE ──
    print("\n[crypto/BRONZE] extract → raw Parquet")
    results: list[ExtractResult] = []
    raw: list[dict] = []
    for name, fn in SOURCES.items():
        try:
            recs = fn()
            bronze.land(name, recs, run_id)
            results.append(ExtractResult(name, recs, ok=True))
            raw += recs
            print(f"   [ok] {name:22} {len(recs):>7,}")
        except Exception as e:  # noqa: BLE001
            results.append(ExtractResult(name, [], ok=False, error=str(e)))
            print(f"   [x]  {name:22} {e}")
    health.record(run_id, results)

    # ── SILVER ──
    print("[crypto/SILVER] dedupe → categorize → link org → crypto_addresses")
    rows = [r for r in _dedupe(raw) if r.get("category") in PRODUCT_CATEGORIES]
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    conn.executemany(
        """INSERT OR REPLACE INTO crypto_addresses
           (address, chain, entity_name, category, topics, is_terror, org, source, collected_date)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [[r["address"], r["chain"], r["entity_name"], r["category"], r.get("topics", ""),
          r.get("is_terror", 0), _link_org(r["entity_name"], r.get("topics", "")),
          r["source"], today] for r in rows],
    )
    conn.commit()

    # ── GOLD ──
    print("[crypto/GOLD] aggregate → crypto_stats")
    conn.execute("DELETE FROM crypto_stats")
    conn.executescript(
        """
        INSERT INTO crypto_stats (scope, key, n, chains)
          SELECT 'total', 'all', COUNT(*), COUNT(DISTINCT chain) FROM crypto_addresses;
        INSERT INTO crypto_stats (scope, key, n, chains)
          SELECT 'total', 'terror', COUNT(*), COUNT(DISTINCT chain) FROM crypto_addresses WHERE is_terror=1;
        INSERT INTO crypto_stats (scope, key, n, chains)
          SELECT 'category', category, COUNT(*), COUNT(DISTINCT chain) FROM crypto_addresses GROUP BY category;
        INSERT INTO crypto_stats (scope, key, n, chains)
          SELECT 'org', org, COUNT(*), COUNT(DISTINCT chain) FROM crypto_addresses WHERE org IS NOT NULL GROUP BY org;
        INSERT INTO crypto_stats (scope, key, n, chains)
          SELECT 'chain', chain, COUNT(*), 1 FROM crypto_addresses GROUP BY chain;
        """
    )
    conn.commit()
    terror = conn.execute("SELECT COUNT(*) FROM crypto_addresses WHERE is_terror=1").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM crypto_addresses").fetchone()[0]
    conn.close()
    print(f"   silver: {total:,} wallets | terror: {terror}")


if __name__ == "__main__":
    run(datetime.now().strftime("manual-%Y%m%d-%H%M%S"))
