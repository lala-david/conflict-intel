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


# OFAC/EU/UN sanction programs that denote terrorism (vs drugs, WMD, cyber, …).
TERROR_PROGRAMS = {"SDGT", "SDT", "FTO", "US-TERR", "EU-TERR", "UN-TERR"}


def fetch_opensanctions(timeout: int = 150) -> list[dict]:
    out: list[dict] = []
    for ds in OS_DATASETS:
        try:
            resp = requests.get(OS_URL.format(ds=ds), timeout=timeout, stream=True)
            resp.raise_for_status()
            entities: dict[str, dict] = {}
            wallets: list[dict] = []
            holder_programs: dict[str, set[str]] = {}
            for raw in resp.iter_lines():
                if not raw:
                    continue
                try:
                    e = json.loads(raw)
                except Exception:
                    continue
                if e.get("id"):
                    entities[e["id"]] = e
                sch = e.get("schema")
                if sch == "CryptoWallet":
                    wallets.append(e)
                elif sch == "Sanction":
                    ep = e.get("properties", {})
                    progs = set(ep.get("program", []) or []) | set(ep.get("programId", []) or [])
                    for tgt in ep.get("entity", []) or []:
                        holder_programs.setdefault(tgt, set()).update(progs)
            for w in wallets:
                p = w.get("properties", {})
                addr = _first(p, "publicKey")
                if not addr:
                    continue
                holder_id = _first(p, "holder") or ""
                holder = entities.get(holder_id, {})
                hp = holder.get("properties", {})
                name = _first(hp, "name") or "Unknown entity"
                topics = hp.get("topics", []) or p.get("topics", []) or []
                programs = holder_programs.get(holder_id, set())
                # terror if the OFAC program says so, or the name/topics hint at it
                terror = bool(programs & TERROR_PROGRAMS) or _is_terror(name + " " + " ".join(topics))
                out.append({
                    "address": addr, "chain": _chain(_first(p, "currency")),
                    "entity_name": name,
                    "topics": ",".join(sorted(programs | set(topics))),
                    "category": "sanction", "is_terror": 1 if terror else 0,
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


# ── NBCTF (Israel counter-terror-financing seizures) ────────────────────────
NBCTF_PAGE = ("nbctf.mod.gov.il/en/Minister%20Sanctions/PropertyPerceptions/"
              "Pages/Blockchain1.aspx")
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58check_ok(s: str) -> bool:
    """Validate a base58check address (BTC 1/3, TRON T…) — filters false positives."""
    import hashlib
    num = 0
    for c in s:
        i = _B58.find(c)
        if i < 0:
            return False
        num = num * 58 + i
    body = num.to_bytes((num.bit_length() + 7) // 8, "big")
    body = b"\x00" * (len(s) - len(s.lstrip("1"))) + body
    if len(body) < 5:
        return False
    payload, checksum = body[:-4], body[-4:]
    return hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] == checksum


def _valid_addr(a: str, chain: str) -> bool:
    if chain == "ETH":
        return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", a))
    if a.startswith("bc1"):
        return 25 <= len(a) <= 62  # bech32 — accept (checksum is bech32, rarely spurious)
    return _b58check_ok(a)


def fetch_nbctf(timeout: int = 60) -> list[dict]:
    """Addresses from Israel's NBCTF crypto-seizure page (via the Wayback Machine —
    the live site blocks bots). All are terrorism-designated seizures."""
    out: list[dict] = []
    try:
        avail = requests.get(
            f"http://archive.org/wayback/available?url={NBCTF_PAGE}", timeout=timeout
        ).json()
        snap = avail.get("archived_snapshots", {}).get("closest", {}).get("url")
        if not snap:
            return out
        text = re.sub(r"<[^>]+>", " ", requests.get(snap, timeout=timeout).text)
        seen: set[str] = set()
        for pat, chain in (
            (r"0x[a-fA-F0-9]{40}", "ETH"),
            (r"T[A-Za-z1-9]{33}", "TRX"),
            (r"bc1[a-z0-9]{20,60}|[13][a-km-zA-HJ-NP-Z1-9]{25,39}", "BTC"),
        ):
            for a in re.findall(pat, text):
                if a in seen or not _valid_addr(a, chain):
                    continue
                seen.add(a)
                out.append({
                    "address": a, "chain": chain,
                    "entity_name": "NBCTF seizure (Israel)",
                    "topics": "terrorism,SEIZURE", "category": "terror", "is_terror": 1,
                    "source": "nbctf",
                })
    except Exception as ex:
        print(f"    [crypto] nbctf 실패: {ex}")
    return out


# ── DOJ terror-forfeiture complaints (PDF address lists) ────────────────────
_BROWSER_UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")}
# file id → (entity label, row-source). 1304296 is the 2020 al-Qassam Brigades
# (Hamas) forfeiture complaint — ~320 BTC addresses (GraphSense only had 155 of them).
DOJ_FORFEITURE = {
    "1304296": ("al-Qassam Brigades (Hamas)", "doj/2020-alqassam-forfeiture"),
}


def fetch_doj_forfeiture(timeout: int = 90) -> list[dict]:
    """Crypto addresses extracted from DOJ terror-forfeiture complaint PDFs."""
    import io
    out: list[dict] = []
    try:
        from pdfminer.high_level import extract_text
    except Exception as ex:  # pdfminer missing
        print(f"    [crypto] doj: pdfminer 없음 ({ex})")
        return out
    for fid, (entity, src) in DOJ_FORFEITURE.items():
        try:
            url = f"https://www.justice.gov/opa/press-release/file/{fid}/download"
            content = requests.get(url, headers=_BROWSER_UA, timeout=timeout).content
            text = extract_text(io.BytesIO(content))
        except Exception as ex:
            print(f"    [crypto] doj/{fid} 실패: {ex}")
            continue
        for a in set(re.findall(r"\b(?:bc1[a-z0-9]{20,60}|[13][a-km-zA-HJ-NP-Z1-9]{25,39})\b", text)):
            if not (a.startswith("bc1") or _b58check_ok(a)):
                continue
            out.append({
                "address": a, "chain": "BTC", "entity_name": entity,
                "topics": "terrorism,DOJ-forfeiture", "category": "terror", "is_terror": 1,
                "source": src,
            })
    return out


# ── Analyst blogs — attribute seized addresses to a specific organization ────
# These posts name the org behind a seizure; the addresses mostly overlap our
# NBCTF set, so ordering this source early attaches the right org to them.
TERROR_BLOGS = {
    "https://www.chainalysis.com/blog/israel-nbctf-hezbollah-iran-quds-crypto-seizure/": "Hezbollah",
    "https://www.chainalysis.com/blog/israel-hamas-cryptocurrency-seizure-july-2021/": "Hamas",
    "https://www.elliptic.co/blog/analysis/israel-orders-seizure-of-crypto-wallets-worth-94-million-linked-to-palestinian-islamic-jihad": "Palestinian Islamic Jihad",
}


def fetch_terror_blogs(timeout: int = 30) -> list[dict]:
    out: list[dict] = []
    for url, org in TERROR_BLOGS.items():
        try:
            text = re.sub(r"<[^>]+>", " ", requests.get(url, headers=_BROWSER_UA, timeout=timeout).text)
        except Exception as ex:
            print(f"    [crypto] blog {url[-30:]} 실패: {ex}")
            continue
        seen: set[str] = set()
        for pat, chain in (
            (r"0x[a-fA-F0-9]{40}", "ETH"),
            (r"T[A-Za-z1-9]{33}", "TRX"),
            (r"bc1[a-z0-9]{20,60}|[13][a-km-zA-HJ-NP-Z1-9]{25,39}", "BTC"),
        ):
            for a in re.findall(pat, text):
                if a in seen or not _valid_addr(a, chain):
                    continue
                seen.add(a)
                out.append({
                    "address": a, "chain": chain, "entity_name": org,
                    "topics": "terrorism,seizure", "category": "terror", "is_terror": 1,
                    "source": "analyst-blog",
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
    everything = (fetch_doj_forfeiture() + fetch_terror_blogs() + fetch_opensanctions()
                  + fetch_graphsense() + fetch_nbctf() + fetch_ransomwhere())
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
