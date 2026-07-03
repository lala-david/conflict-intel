"""
Sanctioned crypto-wallet collector — terror/sanctions financing intelligence.

Pulls CryptoWallet entities from OpenSanctions (the same FollowTheMoney feeds we
already use for sanctions), resolves each wallet's holder (the sanctioned person
or organization), and returns structured records. Downstream we link the holder
name to the conflict organizations we already track.

Only publicly-designated, sanctioned addresses — a defensive threat-intel /
sanctions-screening dataset.
"""
import json
import requests

DATASETS = ["us_ofac_sdn", "eu_sanctions", "un_sc_sanctions"]
FTM_URL = "https://data.opensanctions.org/datasets/latest/{ds}/entities.ftm.json"

# Keywords that flag a holder as terrorism-related (vs. cartel/cyber/etc.)
TERROR_HINTS = (
    "terror", "hamas", "hizballah", "hezbollah", "islamic state", "isil", "isis",
    "daesh", "al-qaida", "al qaeda", "al-qaeda", "al-shabaab", "shabaab",
    "islamic jihad", "pij", "boko haram", "taliban", "houthi", "ansar",
    "jihad", "brigades", "quds force", "irgc", "wagner",
)


def _first(props: dict, key: str):
    v = props.get(key)
    return v[0] if isinstance(v, list) and v else None


def fetch_crypto_wallets(timeout: int = 150) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for ds in DATASETS:
        try:
            resp = requests.get(FTM_URL.format(ds=ds), timeout=timeout, stream=True)
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
                if not addr or addr in seen:
                    continue
                seen.add(addr)
                holder_id = _first(p, "holder")
                holder = entities.get(holder_id or "", {})
                hp = holder.get("properties", {})
                holder_name = _first(hp, "name") or "Unknown entity"
                topics = hp.get("topics", []) or p.get("topics", []) or []
                blob = f"{holder_name} {' '.join(topics)}".lower()
                is_terror = any(h in blob for h in TERROR_HINTS)
                out.append({
                    "address": addr,
                    "chain": _first(p, "currency") or "?",
                    "entity_name": holder_name,
                    "entity_schema": holder.get("schema") or "",
                    "topics": ",".join(topics),
                    "is_terror": 1 if is_terror else 0,
                    "dataset": ds,
                    "source": f"opensanctions/{ds}",
                })
        except Exception as ex:
            print(f"    [crypto] {ds} 실패: {ex}")
    return out


if __name__ == "__main__":
    rows = fetch_crypto_wallets()
    terror = [r for r in rows if r["is_terror"]]
    print(f"총 지갑: {len(rows)} | 테러연계: {len(terror)}")
    chains: dict[str, int] = {}
    for r in rows:
        chains[r["chain"]] = chains.get(r["chain"], 0) + 1
    print("체인별:", dict(sorted(chains.items(), key=lambda x: -x[1])[:12]))
    print("\n테러연계 샘플:")
    for r in terror[:12]:
        print(f"  {r['chain']:5} {r['address'][:44]:44} ← {r['entity_name'][:40]}")
