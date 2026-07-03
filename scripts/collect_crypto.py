"""
Collect sanctioned crypto wallets and link them to the organizations we track.

  python scripts/collect_crypto.py

Fetches wallets (crypto_source), best-effort matches each holder to an actor we
already store in events(actor1), and upserts into the crypto_addresses table.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crypto_source import fetch_crypto_wallets  # noqa: E402
from database import init_db, get_conn  # noqa: E402

# Curated high-precision map: OFAC/OpenSanctions holder-name keywords → canonical
# conflict organization. Only well-known armed groups; everything else stays null.
_ORG_ALIASES: list[tuple[tuple[str, ...], str]] = [
    (("isil", "isis", "islamic state", "daesh", "khorasan", "iswap"), "Islamic State"),
    (("hamas", "al-qassam", "qassam"), "Hamas"),
    (("hizballah", "hezbollah"), "Hezbollah"),
    (("ansarallah", "ansar allah", "houthi"), "Houthis (Ansarallah)"),
    (("al-qaida", "al-qaeda", "al qaeda", "aqap", "aqim", "qaeda"), "al-Qaeda"),
    (("al-shabaab", "al shabaab", "shabaab"), "al-Shabaab"),
    (("palestinian islamic jihad", "islamic jihad", "pij"), "Palestinian Islamic Jihad"),
    (("hayat tahrir", "al-nusra", "nusra", "hts"), "Hayat Tahrir al-Sham"),
    (("irgc", "quds force", "quds"), "IRGC / Quds Force"),
    (("boko haram",), "Boko Haram"),
    (("taliban", "haqqani"), "Taliban / Haqqani"),
    (("wagner",), "Wagner Group"),
    (("hizbul", "lashkar", "jaish-e", "jaish e"), "Kashmir militant groups"),
    (("pkk", "kurdistan workers"), "PKK"),
    (("tehrik-i-taliban", "ttp"), "Tehrik-i-Taliban Pakistan"),
]


def link_orgs(rows: list[dict]) -> int:
    """Label each wallet with a canonical conflict org via a curated alias map."""
    linked = 0
    for r in rows:
        blob = f"{r['entity_name']} {r.get('topics', '')}".lower()
        r["org"] = None
        for keys, canon in _ORG_ALIASES:
            if any(k in blob for k in keys):
                r["org"] = canon
                linked += 1
                break
    return linked


def main():
    init_db()
    print("가상자산 지갑 수집 중 (OpenSanctions)...")
    rows = fetch_crypto_wallets()
    if not rows:
        print("  수집 결과 없음")
        return
    conn = get_conn()
    linked = link_orgs(rows)
    today = datetime.now().strftime("%Y-%m-%d")
    n = 0
    for r in rows:
        conn.execute(
            """INSERT OR REPLACE INTO crypto_addresses
               (address, chain, entity_name, entity_schema, topics, is_terror, org, dataset, source, collected_date)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            [r["address"], r["chain"], r["entity_name"], r["entity_schema"], r["topics"],
             r["is_terror"], r.get("org"), r["dataset"], r["source"], today],
        )
        n += 1
    conn.commit()
    terror = sum(1 for r in rows if r["is_terror"])
    print(f"  저장: {n}개 지갑 | 테러연계: {terror} | 조직 링크됨: {linked}")
    conn.close()


if __name__ == "__main__":
    main()
