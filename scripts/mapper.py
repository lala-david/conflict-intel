"""
기반 데이터 매핑 엔진
- 수집된 사건을 organizations, countries, conflict_zones, classifications DB와 자동 매칭
"""
import json
import math
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


class TerrorMapper:
    """수집 데이터를 기반 DB와 매핑하는 엔진"""

    def __init__(self):
        self.orgs = self._load("organizations.json")
        self.countries = self._load("countries.json")
        self.zones = self._load("conflict_zones.json")
        self.classifications = self._load("classifications.json")

        # 검색용 인덱스 구축
        self._org_index = self._build_org_index()
        self._country_index = self._build_country_index()
        self._zone_list = self.zones.get("conflict_zones", [])

    def _load(self, filename: str) -> dict:
        path = DATA_DIR / filename
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    # ─────────────────────────────────────
    # 인덱스 구축
    # ─────────────────────────────────────
    def _build_org_index(self) -> dict:
        """조직명 → 조직 데이터 매핑 (별칭 포함)"""
        index = {}
        for org in self.orgs.get("un_designated", []):
            name = org.get("name", "").lower().strip()
            if name:
                index[name] = {**org, "designation": "UN"}
            for alias in org.get("aliases", []):
                alias_lower = alias.lower().strip()
                if alias_lower:
                    index[alias_lower] = {**org, "designation": "UN"}

        for org in self.orgs.get("ofac_designated", []):
            name = org.get("name", "").lower().strip()
            if name:
                index[name] = {**org, "designation": "OFAC"}
            for alias in org.get("aliases", []):
                alias_lower = alias.lower().strip()
                if alias_lower:
                    index[alias_lower] = {**org, "designation": "OFAC"}

        return index

    def _build_country_index(self) -> dict:
        """국가명/ISO → 국가 데이터 매핑"""
        index = {}
        regions = self.countries.get("regions", {})
        for region_key, region_data in regions.items():
            for country in region_data.get("countries", []):
                name = country.get("name", "").lower()
                iso2 = country.get("iso_alpha2", "").lower()
                iso3 = country.get("iso_alpha3", "").lower()
                entry = {**country, "region_key": region_key, "region_name": region_data.get("full_name", "")}
                if name:
                    index[name] = entry
                if iso2:
                    index[iso2] = entry
                if iso3:
                    index[iso3] = entry
        return index

    # ─────────────────────────────────────
    # 조직 매칭
    # ─────────────────────────────────────
    def match_organization(self, actor_name: str) -> Optional[dict]:
        """행위자 이름을 지정 조직 DB와 매칭"""
        if not actor_name:
            return None

        actor_lower = actor_name.lower().strip()

        # 1. 정확한 매칭
        if actor_lower in self._org_index:
            org = self._org_index[actor_lower]
            return {
                "matched_name": org.get("name", ""),
                "designation": org.get("designation", ""),
                "countries": org.get("countries", []),
                "topics": org.get("topics", []),
                "match_type": "exact",
            }

        # 2. 부분 매칭 (조직명이 행위자명에 포함되거나 그 반대)
        for org_name, org_data in self._org_index.items():
            if len(org_name) >= 4 and (org_name in actor_lower or actor_lower in org_name):
                return {
                    "matched_name": org_data.get("name", ""),
                    "designation": org_data.get("designation", ""),
                    "countries": org_data.get("countries", []),
                    "topics": org_data.get("topics", []),
                    "match_type": "partial",
                }

        return None

    # ─────────────────────────────────────
    # 국가 매칭
    # ─────────────────────────────────────
    def match_country(self, country_name: str) -> Optional[dict]:
        """국가명/ISO 코드를 국가 DB와 매칭"""
        if not country_name:
            return None

        key = country_name.lower().strip()

        if key in self._country_index:
            c = self._country_index[key]
            return {
                "name": c.get("name", ""),
                "iso": c.get("iso_alpha2", ""),
                "region": c.get("region_name", ""),
                "sub_region": c.get("sub_region", ""),
                "threat_level": c.get("threat_level", "Unknown"),
                "active_groups": c.get("active_threat_groups", []),
                "conflict_zones": c.get("conflict_zones", []),
            }

        return None

    # ─────────────────────────────────────
    # 분쟁 지역 매칭 (좌표 기반)
    # ─────────────────────────────────────
    def match_conflict_zone(self, lat: float, lon: float) -> Optional[dict]:
        """좌표를 분쟁 지역 DB와 매칭 (바운딩 박스)"""
        if not lat or not lon:
            return None

        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            return None

        for zone in self._zone_list:
            bbox = zone.get("bounding_box", {})
            if not bbox:
                continue

            n = bbox.get("north", 0)
            s = bbox.get("south", 0)
            e = bbox.get("east", 0)
            w = bbox.get("west", 0)

            if s <= lat <= n and w <= lon <= e:
                return {
                    "zone_id": zone.get("id", ""),
                    "zone_name": zone.get("zone_name", ""),
                    "country": zone.get("country", ""),
                    "region": zone.get("region", ""),
                    "intensity": zone.get("intensity", ""),
                    "trend": zone.get("recent_trend", ""),
                    "active_groups": zone.get("active_groups", []),
                    "conflict_type": zone.get("conflict_type", ""),
                    "center": zone.get("center_coordinates", {}),
                    "population_at_risk": zone.get("estimated_civilian_population_at_risk", 0),
                }

        # 바운딩 박스에 없으면 가장 가까운 분쟁 지역 찾기 (100km 이내)
        closest = None
        min_dist = float("inf")
        for zone in self._zone_list:
            center = zone.get("center_coordinates", {})
            clat = center.get("lat", 0)
            clon = center.get("lon", 0)
            if not clat or not clon:
                continue
            dist = self._haversine(lat, lon, clat, clon)
            if dist < min_dist:
                min_dist = dist
                closest = zone

        if closest and min_dist <= 100:  # 100km 이내
            return {
                "zone_id": closest.get("id", ""),
                "zone_name": closest.get("zone_name", ""),
                "country": closest.get("country", ""),
                "region": closest.get("region", ""),
                "intensity": closest.get("intensity", ""),
                "trend": closest.get("recent_trend", ""),
                "active_groups": closest.get("active_groups", []),
                "conflict_type": closest.get("conflict_type", ""),
                "distance_km": round(min_dist, 1),
                "match_type": "proximity",
            }

        return None

    # ─────────────────────────────────────
    # 공격 유형 분류
    # ─────────────────────────────────────
    def classify_attack(self, event_type: str, sub_event_type: str = "") -> Optional[dict]:
        """공격 유형을 분류 체계와 매칭"""
        text = f"{event_type} {sub_event_type}".lower()
        attack_types = self.classifications.get("attack_types", {})

        # 키워드 매핑
        mappings = {
            "bombing": ["bomb", "ied", "vbied", "explosive", "landmine", "mine"],
            "armed_assault": ["armed assault", "armed clash", "shooting", "ambush", "raid", "firefight"],
            "assassination": ["assassination", "targeted killing", "targeted"],
            "hostage_kidnapping": ["kidnap", "hostage", "abduct", "hijack"],
            "arson_incendiary": ["arson", "fire", "incendiary", "burn"],
            "melee": ["stab", "knife", "machete", "vehicle ramming", "ram"],
            "shelling": ["shell", "artillery", "missile", "mortar", "rocket"],
            "airstrike": ["airstrike", "air strike", "drone strike", "drone"],
            "cbrn": ["chemical", "biological", "nuclear", "radiological"],
            "cyber": ["cyber", "hack"],
        }

        for category, keywords in mappings.items():
            if any(k in text for k in keywords):
                cat_data = attack_types.get(category, {})
                return {
                    "category": category,
                    "category_name": cat_data.get("name", category),
                    "original_type": event_type,
                    "original_subtype": sub_event_type,
                }

        return {"category": "unknown", "category_name": "Unclassified", "original_type": event_type}

    # ─────────────────────────────────────
    # 전체 사건 매핑
    # ─────────────────────────────────────
    def enrich_event(self, event: dict) -> dict:
        """하나의 사건에 기반 데이터 전부 매핑"""
        enriched = {**event, "_enrichment": {}}

        # 1. 조직 매칭
        actor1 = event.get("actor1", "")
        actor2 = event.get("actor2", "")
        org1 = self.match_organization(actor1)
        org2 = self.match_organization(actor2)
        if org1:
            enriched["_enrichment"]["actor1_org"] = org1
        if org2:
            enriched["_enrichment"]["actor2_org"] = org2

        # 2. 국가 매칭
        country = event.get("country", "") or event.get("country_code", "")
        country_data = self.match_country(country)
        if country_data:
            enriched["_enrichment"]["country"] = country_data

        # 3. 분쟁 지역 매칭
        lat = event.get("latitude", "")
        lon = event.get("longitude", "")
        zone = self.match_conflict_zone(lat, lon)
        if zone:
            enriched["_enrichment"]["conflict_zone"] = zone

        # 4. 공격 유형 분류
        etype = event.get("event_type", "") or event.get("event_code", "")
        subtype = event.get("sub_event_type", "")
        attack = self.classify_attack(etype, subtype)
        if attack:
            enriched["_enrichment"]["attack_classification"] = attack

        return enriched

    def enrich_all(self, data: dict) -> dict:
        """전체 수집 데이터에 기반 매핑 적용"""
        enriched = {}
        stats = {"total_enriched": 0, "org_matches": 0, "country_matches": 0, "zone_matches": 0}

        for source_key in ["acled", "gdelt"]:
            events = data.get(source_key, [])
            enriched_events = []
            for event in events:
                e = self.enrich_event(event)
                enrichment = e.get("_enrichment", {})
                if enrichment.get("actor1_org") or enrichment.get("actor2_org"):
                    stats["org_matches"] += 1
                if enrichment.get("country"):
                    stats["country_matches"] += 1
                if enrichment.get("conflict_zone"):
                    stats["zone_matches"] += 1
                stats["total_enriched"] += 1
                enriched_events.append(e)
            enriched[source_key] = enriched_events

        # 나머지 소스는 그대로 유지
        for key in data:
            if key not in enriched:
                enriched[key] = data[key]

        enriched["_enrichment_stats"] = stats
        return enriched

    # ─────────────────────────────────────
    # 유틸리티
    # ─────────────────────────────────────
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """두 좌표 간 거리 (km)"""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.asin(math.sqrt(a))
