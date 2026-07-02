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


class ConflictMapper:
    """수집 데이터를 기반 DB와 매핑하는 엔진"""

    def __init__(self):
        self.orgs = self._load("organizations.json")
        self.countries = self._load("countries.json")
        self.zones = self._load("conflict_zones.json")
        self.classifications = self._load("classifications.json")

        # 검색용 인덱스 구축
        self._org_index = self._build_org_index()
        self._alias_index = self._build_alias_index()
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
        """조직명 + 인물명 → 데이터 매핑 (별칭 포함)"""
        index = {}

        # 조직
        for org in self.orgs.get("organizations", []):
            name = org.get("name", "").lower().strip()
            source = org.get("source", "")
            if name:
                index[name] = {**org, "designation": source, "entity_type": "organization"}
            for alias in org.get("aliases", []):
                alias_lower = alias.lower().strip()
                if alias_lower:
                    index[alias_lower] = {**org, "designation": source, "entity_type": "organization"}

        # 인물
        for person in self.orgs.get("persons", []):
            name = person.get("name", "").lower().strip()
            source = person.get("source", "")
            if name:
                index[name] = {**person, "designation": source, "entity_type": "person"}
            for alias in person.get("aliases", []):
                alias_lower = alias.lower().strip()
                if alias_lower:
                    index[alias_lower] = {**person, "designation": source, "entity_type": "person"}

        return index

    def _build_country_index(self) -> dict:
        """국가명/ISO/별칭 → 국가 데이터 매핑"""
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
                # aliases (e.g. "Burma" → Myanmar, "DR Congo (Zaire)" → DRC)
                for alias in country.get("aliases", []) or []:
                    a = (alias or "").lower().strip()
                    if a and a not in index:
                        index[a] = entry
        return index

    def _build_alias_index(self) -> dict:
        """조직/인물의 모든 이름·별칭을 하나의 flat dict로 구축 + 약어 매핑"""
        index = {}

        # 1. organizations.json 에서 name + aliases 등록
        for org in self.orgs.get("organizations", []):
            name = org.get("name", "").strip()
            source = org.get("source", "")
            entry = {**org, "designation": source, "entity_type": "organization"}
            if name:
                index[name.lower()] = entry
            for alias in org.get("aliases", []):
                a = alias.strip()
                if a:
                    index[a.lower()] = entry

        for person in self.orgs.get("persons", []):
            name = person.get("name", "").strip()
            source = person.get("source", "")
            entry = {**person, "designation": source, "entity_type": "person"}
            if name:
                index[name.lower()] = entry
            for alias in person.get("aliases", []):
                a = alias.strip()
                if a:
                    index[a.lower()] = entry

        # 2. 잘 알려진 약어 매핑 (모호하지 않은 것만)
        _abbreviations = {
            "hts": "Hay'at Tahrir al-Sham",
            "ttp": "Tehrik-e Taliban Pakistan (TTP)",
            "pkk": "Kurdistan Workers Party (PKK)",
            "bla": "Balochistan Liberation Army",
            "rsf": "Rapid Support Forces",
            "eln": "ELN",
            "m23": "M23",
            "isil": "Islamic State in Iraq and the Levant",
            "isis": "Islamic State in Iraq and the Levant",
            "daesh": "Islamic State in Iraq and the Levant",
            "islamic state": "Islamic State in Iraq and the Levant",
            "is": None,  # too ambiguous, skip
            "al qaeda": "Al-Qaida",
            "al qaida": "Al-Qaida",
            "al-qaeda": "Al-Qaida",
            "hezbollah": "Hizballah",
            "hizbollah": "Hizballah",
            "houthi": "Ansarallah",
            "houthis": "Ansarallah",
            "houthi rebels": "Ansarallah",
            "ansar allah": "Ansarallah",
            "boko haram": "Jama'atu Ahlis Sunna Lidda'awati Wal-Jihad",
            "al-shabaab": "Al-Shabaab",
            "al shabaab": "Al-Shabaab",
            "al shabab": "Al-Shabaab",
            "jnim": "Jama'a Nusrat ul-Islam wa al-Muslimin (JNIM)",
            "iswap": "Islamic State West Africa Province (ISWAP)",
            "hamas": "Hamas",
            "wagner": "Wagner Group",
            "wagner group": "Wagner Group",
        }

        for abbr, target_name in _abbreviations.items():
            if target_name is None:
                continue
            abbr_lower = abbr.lower()
            if abbr_lower in index:
                continue  # 이미 존재하면 덮어쓰지 않음
            # 대상 이름이 인덱스에 있으면 같은 entry 재사용
            target_lower = target_name.lower()
            if target_lower in index:
                index[abbr_lower] = index[target_lower]
            else:
                # 인덱스에 없는 조직이면 최소 entry 생성
                index[abbr_lower] = {
                    "name": target_name,
                    "aliases": [],
                    "countries": [],
                    "topics": [],
                    "designation": "",
                    "entity_type": "organization",
                }

        return index

    # ─────────────────────────────────────
    # 조직 매칭 (exact + alias only, no partial)
    # ─────────────────────────────────────
    def match_organization(self, actor_name: str) -> Optional[dict]:
        """행위자 이름을 alias index와 정확 매칭 (부분 매칭 없음)"""
        if not actor_name:
            return None

        actor_lower = actor_name.strip().lower()

        # 1. 정확 매칭
        if actor_lower in self._alias_index:
            org = self._alias_index[actor_lower]
            # 원래 이름과 동일하면 exact, 아니면 alias
            match_type = "exact" if actor_lower == org.get("name", "").lower() else "alias"
            return {
                "matched_name": org.get("name", ""),
                "designation": org.get("designation", ""),
                "countries": org.get("countries", []),
                "topics": org.get("topics", []),
                "match_type": match_type,
            }

        # 2. "the " 접두사 제거 후 재시도
        if actor_lower.startswith("the "):
            stripped = actor_lower[4:]
            if stripped in self._alias_index:
                org = self._alias_index[stripped]
                match_type = "exact" if stripped == org.get("name", "").lower() else "alias"
                return {
                    "matched_name": org.get("name", ""),
                    "designation": org.get("designation", ""),
                    "countries": org.get("countries", []),
                    "topics": org.get("topics", []),
                    "match_type": match_type,
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
        if lat is None or lon is None:
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
            if clat is None or clon is None:
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

    def match_conflict_zone_by_text(self, country: str, location: str = "") -> Optional[dict]:
        """#7: 텍스트 기반 분쟁 지역 매칭 (좌표 없을 때 폴백)"""
        if not country:
            return None
        country_lower = country.lower().strip()
        location_lower = location.lower().strip() if location else ""

        best_match = None
        best_score = 0
        for zone in self._zone_list:
            zone_country = zone.get("country", "").lower()
            zone_name = zone.get("zone_name", "").lower()
            zone_locations = [loc.lower() for loc in zone.get("key_locations", [])]

            score = 0
            if country_lower in zone_country or zone_country in country_lower:
                score += 1
                if location_lower:
                    if location_lower in zone_name:
                        score += 3
                    for loc in zone_locations:
                        if loc in location_lower or location_lower in loc:
                            score += 2
                            break

            if score > best_score:
                best_score = score
                best_match = zone

        if best_match and best_score >= 1:
            return {
                "zone_id": best_match.get("id", ""),
                "zone_name": best_match.get("zone_name", ""),
                "country": best_match.get("country", ""),
                "region": best_match.get("region", ""),
                "intensity": best_match.get("intensity", ""),
                "trend": best_match.get("recent_trend", ""),
                "active_groups": best_match.get("active_groups", []),
                "conflict_type": best_match.get("conflict_type", ""),
                "match_type": "text",
                "match_score": best_score,
            }
        return None

    # ─────────────────────────────────────
    # 공격 유형 분류
    # ─────────────────────────────────────
    # CAMEO 이벤트 코드 → 공격 유형 매핑
    CAMEO_TO_ATTACK = {
        "18": "armed_assault", "180": "armed_assault",
        "181": "bombing", "182": "armed_assault", "183": "cbrn",
        "184": "armed_assault", "185": "armed_assault", "186": "armed_assault",
        "190": "armed_assault", "191": "assassination", "192": "armed_assault",
        "193": "armed_assault", "194": "shelling", "195": "airstrike",
        "196": "armed_assault",
        "200": "bombing", "201": "bombing", "202": "armed_assault",
        "203": "armed_assault", "204": "cbrn",
    }

    def classify_attack(self, event_type: str, sub_event_type: str = "", event_code: str = "") -> Optional[dict]:
        """공격 유형을 분류 체계와 매칭 (CAMEO 코드 우선 → 키워드 폴백)"""
        attack_types = self.classifications.get("attack_types", {})

        # 1. CAMEO 코드 매핑 (GDELT 이벤트)
        if event_code:
            category = self.CAMEO_TO_ATTACK.get(str(event_code))
            if category:
                cat_data = attack_types.get(category, {})
                return {
                    "category": category,
                    "category_name": cat_data.get("name", category),
                    "original_type": event_type,
                    "original_subtype": sub_event_type,
                }

        # 2. 키워드 매핑 (ACLED 등 텍스트 기반)
        text = f"{event_type} {sub_event_type}".lower()
        # armed_assault를 arson보다 먼저 배치 (firefight→fire 오분류 방지)
        mappings = [
            ("bombing", ["bomb", "ied", "vbied", "explosive", "landmine", "mine", "suicide"]),
            ("armed_assault", ["armed assault", "armed clash", "shooting", "ambush", "raid", "firefight", "gunfire"]),
            ("assassination", ["assassination", "targeted killing", "targeted"]),
            ("hostage_kidnapping", ["kidnap", "hostage", "abduct", "hijack"]),
            ("shelling", ["shell", "artillery", "missile", "mortar", "rocket"]),
            ("airstrike", ["airstrike", "air strike", "drone strike", "drone"]),
            ("arson_incendiary", ["arson", "incendiary", "burn", "firebomb"]),
            ("melee", ["stab", "knife", "machete", "vehicle ramming", "ram"]),
            ("cbrn", ["chemical", "biological", "nuclear", "radiological"]),
            ("cyber", ["cyber", "hack"]),
        ]

        for category, keywords in mappings:
            if any(k in text for k in keywords):
                cat_data = attack_types.get(category, {})
                return {
                    "category": category,
                    "category_name": cat_data.get("name", category),
                    "original_type": event_type,
                    "original_subtype": sub_event_type,
                }

        # 키워드 매칭 실패 — 폭력/테러 의미 시그널 있는지 폴백 검사
        violence_signals = (
            "kill", "dead", "massacre", "slain", "casualt", "wounded",
            "attack", "militant", "extremist", "insurgent", "guerrilla",
            "terror", "jihad", "violence",
        )
        if any(s in text for s in violence_signals):
            cat_data = attack_types.get("armed_violence", {})
            return {
                "category": "armed_violence",
                "category_name": cat_data.get("name", "armed_violence"),
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

        # 3. 분쟁 지역 매칭 (좌표 우선 → 텍스트 폴백)
        lat = event.get("latitude", "")
        lon = event.get("longitude", "")
        zone = self.match_conflict_zone(lat, lon)
        if not zone:
            # #7: 좌표 없으면 텍스트 기반 매칭
            zone = self.match_conflict_zone_by_text(country, event.get("location", ""))
        if zone:
            enriched["_enrichment"]["conflict_zone"] = zone

        # 4. 공격 유형 분류 (CAMEO 코드 우선)
        etype = event.get("event_type", "")
        subtype = event.get("sub_event_type", "")
        ecode = event.get("event_code", "")
        attack = self.classify_attack(etype, subtype, event_code=ecode)
        if attack:
            enriched["_enrichment"]["attack_classification"] = attack

        return enriched

    def enrich_all(self, data: dict) -> dict:
        """전체 수집 데이터에 기반 매핑 적용"""
        enriched = {}
        stats = {"total_enriched": 0, "org_matches": 0, "country_matches": 0, "zone_matches": 0}

        # 모든 이벤트성 소스에 enrichment 적용 (sanctions는 entity 형식이라 제외)
        for source_key in ["ucdp", "gdelt", "wikipedia", "expert_rss", "google_news", "nctc", "ofac"]:
            events = data.get(source_key, [])
            enriched_events = []
            for event in events:
                # RSS/news 항목에 country가 비어있으면 텍스트+URL 도메인에서 추정
                if source_key in ("expert_rss", "google_news") and not event.get("country"):
                    text = (event.get("title", "") or "") + " | " + (event.get("summary", "") or "")
                    iso = self._guess_iso_from_text(text, event.get("url", ""))
                    if iso:
                        country_data = self.match_country(iso)
                        if country_data:
                            event["country"] = country_data.get("name", "")
                            event["country_code"] = country_data.get("iso", iso)

                # wikipedia: country 필드에 영어명이 있으니 ISO도 채움
                if source_key == "wikipedia" and event.get("country") and not event.get("country_code"):
                    cd = self.match_country(event["country"])
                    if cd:
                        event["country_code"] = cd.get("iso", "")

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

    def _guess_iso_from_text(self, text: str, url: str = "") -> str:
        """뉴스/RSS 본문에서 가장 많이 언급된 국가의 ISO 코드 반환.

        - 다국가 기사에서 set 해시 순서로 잘못 골라지는 문제 방지.
        - 제목(`|` 앞부분)은 본문보다 3배 가중치.
        - URL 도메인이 알려진 자국 매체면 +5 (강한 시그널).
        - 본문에서 한 건도 못 찾으면 도메인만으로 결정.
        """
        if not text and not url:
            return ""
        import re
        from event_linker import CITY_TO_COUNTRY, _domain_country
        title, _, body = text.partition("|") if text else ("", "", "")
        counts: dict[str, int] = {}
        for src, weight in ((title.lower(), 3), (body.lower(), 1)):
            if not src:
                continue
            for city, iso in CITY_TO_COUNTRY.items():
                if len(city) <= 2:
                    continue
                n = len(re.findall(r'\b' + re.escape(city) + r'\b', src))
                if n:
                    counts[iso] = counts.get(iso, 0) + n * weight
        domain_iso = _domain_country(url) if url else ""
        if domain_iso:
            counts[domain_iso] = counts.get(domain_iso, 0) + 5
        if not counts:
            return ""
        return max(counts.items(), key=lambda kv: kv[1])[0]

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
