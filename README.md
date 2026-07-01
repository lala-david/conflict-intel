<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=28&duration=3000&pause=1000&color=FFFFFF&center=true&vCenter=true&width=640&lines=Conflict+%26+Security+Intelligence">
    <img alt="Conflict & Security Intelligence" src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=28&duration=3000&pause=1000&color=000000&center=true&vCenter=true&width=640&lines=Conflict+%26+Security+Intelligence">
  </picture>
</p>

<p align="center">
  <em>Real-time Global Conflict Intelligence Platform</em>
</p>

<p align="center">
  <a href="#about"><img src="https://img.shields.io/badge/status-operational-00c853?style=flat-square" alt="Status" /></a>
  <a href="#data-coverage"><img src="https://img.shields.io/badge/coverage-160%2B_countries-448aff?style=flat-square" alt="Coverage" /></a>
  <a href="#data-coverage"><img src="https://img.shields.io/badge/data_span-37_years-7c4dff?style=flat-square" alt="Data" /></a>
  <a href="#daily-intelligence-report"><img src="https://img.shields.io/badge/updates-daily_automated-ff6d00?style=flat-square" alt="Updates" /></a>
</p>

---

## About

전 세계에서 발생하는 무력 충돌, 테러, 내전, 반란을 **매일 자동으로 수집하고 분석**하는 인텔리전스 플랫폼입니다.

9개 이상의 독립 데이터 소스(UCDP · GDELT · 공개 Telegram OSINT · 전문 RSS · 제재 등)를 교차 검증하여 단일 소스 편향을 제거하고, 분석가 · 연구자 · 저널리스트에게 **추적 가능한 분쟁 데이터**를 제공합니다.

---

## Pipeline — Medallion (Bronze → Silver → Gold)

```mermaid
graph LR
    S["9 sources\nparallel connectors"] --> B["BRONZE\nraw Parquet\n(immutable)"]
    B --> Si["SILVER\nenrich · link · dedup\n→ events"]
    Si --> G["GOLD\naggregates + brief"]
    G --> D["Dashboard\n+ REST API"]

    linkStyle default stroke-width:2px
```

<table>
<tr>
<td width="50%" valign="top">

**Bronze — immutable raw**

9개 소스 커넥터가 병렬 수집한 원본을 파티션된
**Parquet**(`data/bronze/{source}/dt=날짜/`)으로 불변 적재합니다.
재수집 없이 재처리(replay)가 가능한 원천입니다.

</td>
<td width="50%" valign="top">

**Silver → Gold**

정규화 · dedup · 엔티티 매칭 · 교차 링크 후 `events` 테이블(Silver)로,
국가/조직/카테고리 집계(Gold)로 승격됩니다.
소스별 **헬스 관측성**(count/ok/error)이 매 실행 기록됩니다.

</td>
</tr>
</table>

> 모듈형 커넥터 레지스트리 — 새 소스는 한 줄로 추가. `docker compose up -d scheduler` 로 상시 수집.

---

## Architecture

```
                ┌─────────────────────────────────────────────────────────────┐
                │                                                             │
  ╔═══════════╗ │  ┌───────────┐  ┌───────────┐  ┌────────┐  ┌──────────┐   │  ╔════════════╗
  ║  Global   ║─┤  │           │  │           │  │        │  │          │   ├──║  Dashboard ║
  ║ Event DB  ║ │  │ Collector │─▶│ Enricher  │─▶│ Linker │─▶│ Analyzer │   │  ╠════════════╣
  ╠═══════════╣ │  │           │  │           │  │        │  │          │   │  ║  REST API  ║
  ║ Conflict  ║─┤  └───────────┘  └───────────┘  └────────┘  └──────────┘   ├──╠════════════╣
  ║    DB     ║ │                                                             │  ║ Daily Brief║
  ╠═══════════╣ │   parallel        entity         cross        threat        ├──╠════════════╣
  ║ News &    ║─┤   ingestion      matching       reference    scoring        │  ║  Widgets   ║
  ║   RSS     ║ │                                                             │  ╚════════════╝
  ╠═══════════╣ │                                                             │
  ║ Sanctions ║─┤              I N T E L L I G E N C E    E N G I N E        │
  ╠═══════════╣ │                                                             │
  ║   OSINT   ║─┤                                                             │
  ╚═══════════╝ └─────────────────────────────────────────────────────────────┘
    SOURCES                                                                      OUTPUT
```

---

## Dashboard

웹 대시보드에서 전 세계 분쟁 상황을 실시간으로 탐색할 수 있습니다.

| Page | Description |
|:-----|:------------|
| **Home** | 글로벌 현황 — 인터랙티브 지도, 37년 타임라인, 핫스팟, 실시간 피드 |
| **Countries** | 국가별 위협도, 사건 추이, 활동 단체 프로필 |
| **Organizations** | 무장단체 · 테러조직 활동 이력 및 연관 분석 |
| **Categories** | 분쟁 유형별 분류 — 테러, 내전, 반란, 카르텔 등 |
| **Events** | 개별 사건 검색 · 필터링 · 상세 보기 · CSV 내보내기 |
| **Daily Brief** | 일일 인텔리전스 보고서 |
| **Weekly** | 주간 요약 리포트 |
| **Widgets** | 외부 사이트 임베드용 지도 · 피드 · 배지 |

---

## Daily Intelligence Report

매일 자동 생성되는 보고서는 다음과 같은 구조를 따릅니다.

```mermaid
graph TD
    R["Daily Intelligence Brief"]

    R --> A["BLUF\n핵심 판단 3~5줄"]
    R --> B["Threat Assessment\n국가별 위협 수준"]
    R --> C["Conflict Events\nUCDP · GDELT 사건"]
    R --> D["News Clusters\n교차 매칭 뉴스"]
    R --> E["Org Tracking\n조직 동향"]
    R --> F["Hotspots & Sanctions\n핫스팟 · 제재"]
```

> **BLUF**(Bottom Line Up Front)만 AI가 생성하며, 모든 수치와 분석은 원시 데이터에서 직접 도출됩니다.

---

## Data Coverage

|   | Metric | Detail |
|:--|:-------|:-------|
| **Time** | 1989 — Present | 37년 이상의 분쟁 데이터 |
| **Geography** | 160+ countries | 글로벌 커버리지 |
| **Updates** | Daily | GitHub Actions 자동화 |
| **Classification** | 10 categories | 학술 표준 기반 |
| **Sources** | 9+ independent | UCDP · GDELT · Telegram OSINT · RSS · Sanctions · OFAC · NCTC 등 |
| **Storage** | Bronze/Silver/Gold | Parquet(raw) + SQLite(serving) |

---

## API

<details>
<summary><b>Available Endpoints</b></summary>

<br/>

```
GET  /api/stats              글로벌 통계
GET  /api/events             이벤트 검색 & 필터
GET  /api/events/:id         이벤트 상세
GET  /api/countries          국가별 현황
GET  /api/countries/:name    국가 상세
GET  /api/orgs               조직 정보
GET  /api/orgs/:slug         조직 상세
GET  /api/threats            위협 분석
GET  /api/threats/:name      국가별 위협 상세
GET  /api/hotspots           지리적 핫스팟
GET  /api/sparks             스파크라인 데이터
GET  /api/export/csv         CSV 내보내기
GET  /api/status             시스템 상태
```

</details>

---

## Getting Started

```bash
git clone https://github.com/lala-david/terror_researcher.git && cd terror_researcher
cp .env.example .env                 # OPENAI_API_KEY, UCDP_TOKEN
gh release download db-latest --pattern terror.db --dir data   # optional: seed the DB

# ── Run the pipeline ──
# A) Docker (recommended — runs anywhere)
docker compose run --rm pipeline     # one-shot: bronze → silver → gold
docker compose up -d scheduler       # continuous daily collection

# B) Local
pip install -r requirements.txt
python scripts/pipeline/run.py        # medallion pipeline

# ── Dashboard ──
cd web && npm install && npm run dev
```

Handy: `make pipeline` · `make docker-schedule` · `make health` · `make web`.

<details>
<summary><b>Project Structure</b></summary>

<br/>

```
terror_researcher/
├── scripts/
│   ├── pipeline/           # Medallion pipeline
│   │   ├── base.py             Connector interface
│   │   ├── registry.py         Source registry (add a source in 1 line)
│   │   ├── bronze.py           Immutable raw → partitioned Parquet
│   │   ├── health.py           Per-source observability
│   │   └── run.py              Orchestrator (bronze → silver → gold)
│   ├── sources.py          Source collectors (GDELT, UCDP, RSS, …)
│   ├── telegram_source.py  Public Telegram OSINT (t.me/s scraping)
│   ├── mapper.py           Entity matching & enrichment (Silver)
│   ├── event_linker.py     Cross-source clustering (Silver)
│   ├── threat_scorer.py    Threat scoring & hotspots
│   └── compute_stats.py    Serving aggregates (Gold)
├── web/            # Dashboard & REST API (Next.js) — node tracking + maps
├── data/           # Reference data · terror.db (Silver/Gold) · bronze/ (Parquet)
├── reports/        # Auto-generated daily/weekly briefs
├── Dockerfile · docker-compose.yml · Makefile
└── .github/        # CI/CD automation
```

</details>

---

## Roadmap — Knowledge Graph / Ontology

정규화된 이벤트 위에 **온톨로지 + 지식그래프**를 단계적으로 입힙니다: 엔티티 해소(행위자·장소) →
관계 모델(Event–Actor–Place–Source, 동맹/분파) → 링크 분석 · 관계 추론. 기존 벤더 표준
(SEM · schema.org Event · W3C PROV · STIX)을 재사용하고, 규모에 맞는 경량 그래프로 시작합니다.

---

<p align="center">
  This project is for <b>research and educational purposes</b>.<br/>
  All data is sourced from publicly available OSINT providers.
</p>

<p align="center">
  <sub>Built for researchers, analysts, and anyone who believes transparency saves lives.</sub>
</p>
