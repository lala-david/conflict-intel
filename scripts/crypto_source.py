"""
Illicit / threat-finance crypto-wallet collector — multi-source aggregator.

Pulls publicly-attributed crypto addresses from several open sources and merges
them (deduped by address), tagging each with a category and a terror flag:

  1. OpenSanctions  — OFAC / EU / UN CryptoWallet entities (sanctioned, attributed)
  2. GraphSense TagPacks — open attribution packs (al-Qaeda terrorism, OFAC,
       ransomware, mixers, hacks, scams) with a DOJ/authority source
  3. Ransomwhere    — the public ransomware payment-address database (~11k)

All are public, defensive threat-intelligence datasets. `is_terror` marks the
subset attributed to terrorist organizations.
"""
import json
import re

import requests
import yaml

# ── source config ──────────────────────────────────────────────────────────
OS_DATASETS = ["us_ofac_sdn", "eu_sanctions", "un_sc_sanctions"]
OS_URL = "https://data.opensanctions.org/datasets/latest/{ds}/entities.ftm.json"
GS_API = "https://api.github.com/repos/graphsense/graphsense-tagpacks/contents/packs"
GS_RAW = "https://raw.githubusercontent.com/graphsense/graphsense-tagpacks/master/packs/{name}"
RW_URL = "https://api.ransomwhe.re/export"

TERROR_HINTS = (
    "terror", "hamas", "hizballah", "hezbollah", "islamic state", "isil", "isis",
    "daesh", "al-qaida", "al qaeda", "al-qaeda", "alqaeda", "al-shabaab", "shabaab",
    "islamic jihad", "pij", "boko haram", "taliban", "houthi", "ansarallah", "ansar",
    "jihad", "al-qassam", "qassam", "quds",
)

_CHAIN = {"XBT": "BTC", "BITCOIN": "BTC", "ETHEREUM": "ETH", "TRON": "TRX",
          "LITECOIN": "LTC", "MONERO": "XMR", "ZCASH": "ZEC", "DASH": "DASH",
          "BITCOINCASH": "BCH", "BITCOIN CASH": "BCH"}


def _chain(c: str | None) -> str:
    c = (c or "").upper().strip()
    return _CHAIN.get(c, c or "?")


def _is_terror(text: str) -> bool:
    t = text.lower()
    return any(h in t for h in TERROR_HINTS)


def _first(props: dict, key: str):
    v = props.get(key)
    return v[0] if isinstance(v, list) and v else None


# ── 1. OpenSanctions ────────────────────────────────────────────────────────
def fetch_opensanctions(timeout: int = 150) -> list[dict]:
    out: list[dict] = []
    for ds in OS_DATASETS:
        try:
            resp = requests.get(OS_URL.format(ds=ds), timeout=timeout, stream=True)
            resp.raise_for_status()
            entities: dict[str, dict] = {}
            wallets: list[dict] = []
            for raw in resp.iter_lines():
                if not raw:
                    continue
                try:
                    e = json.loads(raw)
                except Exception:
                    continue
                if e.get("id"):
                    entities[e["id"]] = e
                if e.get("schema") == "CryptoWallet":
                    wallets.append(e)
            for w in wallets:
                p = w.get("properties", {})
                addr = _first(p, "publicKey")
                if not addr:
                    continue
                holder = entities.get(_first(p, "holder") or "", {})
                hp = holder.get("properties", {})
                name = _first(hp, "name") or "Unknown entity"
                topics = hp.get("topics", []) or p.get("topics", []) or []
                out.append({
                    "address": addr, "chain": _chain(_first(p, "currency")),
                    "entity_name": name, "topics": ",".join(topics),
                    "category": "sanction", "is_terror": 1 if _is_terror(name + " " + " ".join(topics)) else 0,
                    "source": f"opensanctions/{ds}",
                })
        except Exception as ex:
            print(f"    [crypto] opensanctions/{ds} 실패: {ex}")
    return out


# ── 2. GraphSense TagPacks ──────────────────────────────────────────────────
def fetch_graphsense(timeout: int = 60) -> list[dict]:
    out: list[dict] = []
    try:
        packs = requests.get(GS_API, timeout=timeout).json()
        names = [f["name"] for f in packs if f.get("name", "").endswith(".yaml")]
    except Exception as ex:
        print(f"    [crypto] graphsense 목록 실패: {ex}")
        return out
    for name in names:
        try:
            doc = yaml.safe_load(requests.get(GS_RAW.format(name=name), timeout=timeout).text)
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        p_label = doc.get("label") or doc.get("title") or name.replace(".yaml", "")
        p_abuse = (doc.get("abuse") or "").lower()
        p_cur = doc.get("currency")
        for tag in doc.get("tags", []) or []:
            if not isinstance(tag, dict):
                continue
            addr = tag.get("address")
            if not addr:
                continue
            label = tag.get("label") or p_label
            abuse = (tag.get("abuse") or p_abuse or "").lower()
            terror = "terror" in abuse or _is_terror(label)
            cat = ("terror" if terror else
                   "ransomware" if "ransom" in abuse else
                   "sanction" if "sanction" in abuse or "ofac" in name.lower() else
                   "mixer" if "mixer" in abuse or "tornado" in name.lower() else
                   "scam" if "scam" in abuse or "fraud" in abuse else
                   "hack" if "hack" in abuse or "hack" in name.lower() else
                   (abuse or "illicit"))
            out.append({
                "address": addr, "chain": _chain(tag.get("currency") or p_cur),
                "entity_name": label, "topics": abuse,
                "category": cat, "is_terror": 1 if terror else 0,
                "source": f"graphsense/{name.replace('.yaml', '')}",
            })
    return out


# ── 3. Ransomwhere ──────────────────────────────────────────────────────────
def fetch_ransomwhere(timeout: int = 60) -> list[dict]:
    out: list[dict] = []
    try:
        data = requests.get(RW_URL, timeout=timeout).json()
        rows = data.get("result", data if isinstance(data, list) else [])
        for r in rows:
            addr = r.get("address")
            if not addr:
                continue
            out.append({
                "address": addr, "chain": _chain(r.get("blockchain")),
                "entity_name": r.get("family") or "Unknown ransomware",
                "topics": "ransomware", "category": "ransomware", "is_terror": 0,
                "source": "ransomwhere",
            })
    except Exception as ex:
        print(f"    [crypto] ransomwhere 실패: {ex}")
    return out


# ── aggregate + dedupe ──────────────────────────────────────────────────────
def fetch_crypto_wallets() -> list[dict]:
    """All sources merged, deduped by address (terror-attributed wins)."""
    everything = fetch_opensanctions() + fetch_graphsense() + fetch_ransomwhere()
    by_addr: dict[str, dict] = {}
    for r in everything:
        a = (r.get("address") or "").strip()
        if not a or len(a) < 8 or not re.match(r"^(0x)?[a-zA-Z0-9:._-]+$", a):
            continue
        prev = by_addr.get(a)
        # prefer a terror-attributed record, otherwise keep the first seen
        if prev is None or (r["is_terror"] and not prev["is_terror"]):
            by_addr[a] = r
    return list(by_addr.values())


if __name__ == "__main__":
    rows = fetch_crypto_wallets()
    terror = [r for r in rows if r["is_terror"]]
    cats: dict[str, int] = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    print(f"총 지갑: {len(rows):,} | 테러연계: {len(terror):,}")
    print("카테고리별:", dict(sorted(cats.items(), key=lambda x: -x[1])))
    print("\n테러 샘플:")
    for r in terror[:10]:
        print(f"  {r['chain']:5} {r['address'][:40]:40} ← {r['entity_name'][:35]} [{r['source']}]")
