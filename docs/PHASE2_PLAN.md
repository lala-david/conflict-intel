# Conflict Researcher — V2 Upgrade Plan

> Phase 1 감사 결과 기반 | 2026-04-13
>
> V1 현황: 22/22 spec 구현, 420K events, 21 pages, 지도 작동
> V2 목표: **성능 · 콘텐츠 밀도 · 비즈니스 연결 · 바이럴** 강화

---

## 1. V1 감사 결과 — 핵심 문제

### 🔴 Critical (사용자 이탈 유발)

| # | 문제 | 데이터 |
|---|------|--------|
| **C1** | `/countries` 5.4초, `/countries/Nigeria` 15초 | dev 서버 기준 (prod도 느릴 것) |
| **C2** | Threat Index 3/100 — 최근 7일 데이터 부족 | UCDP 2개월 지연 + GDELT 사망자 0 |
| **C3** | Hot Regions 1개, Recent Events 5개 — 홈이 비어 보임 | 30일 윈도우에 사건 부족 |
| **C4** | 지도가 iframe (map-test.html) — 필터/인터랙션 제한 | React 통합 실패 대응 |

### 🟡 High (사용자 경험 저하)

| # | 문제 |
|---|------|
| H1 | 검색 기능 없음 — 420K 이벤트 탐색 불가 |
| H2 | 모바일 메뉴 없음 (nav 잘림) |
| H3 | 지도에서 국가 클릭 → 페이지 이동 안 됨 |
| H4 | 37년 타임라인 스크러버 없음 (핵심 차별점인데 미구현) |
| H5 | OG 이미지 없음 → SNS 공유 시 텍스트만 표시 |
| H6 | 위젯 쇼케이스에 실제 미리보기 안 보임 (iframe 로딩 실패) |

### 🟢 Polish (완성도)

| # | 문제 |
|---|------|
| P1 | 각 페이지별 로딩 스켈레톤 없음 |
| P2 | 국가 페이지에 활동 무장단체 목록 + 링크 없음 |
| P3 | 국가 페이지에 전문가 분석 피드 없음 |
| P4 | 데이터 신선도 표시 없음 (각 소스 마지막 업데이트 시각) |
| P5 | 다크/라이트 테마 토글 없음 |

---

## 2. V2 핵심 전략

### 성능 전략

```
문제: dev 서버에서 /countries/Nigeria 15초
원인: 89,000 UCDP 이벤트 실시간 쿼리 (SSR)

해결:
1. pre-computed stats 테이블 (daily batch)
   → 국가별/조직별 통계를 매일 1회 집계해서 별도 테이블에 저장
   → SSR에서 420K scan 대신 1-row lookup
   
2. Static Generation (SSG) for top 30 countries
   → 빌드 시점에 상위 30개국 pre-render
   → ISR 1시간으로 자동 갱신
   
3. Edge caching (Vercel)
   → API routes에 stale-while-revalidate
   
4. 페이지 쿼리 최적화
   → LIMIT 줄이기, 불필요한 JOIN 제거
   → 국가 timeline: year 단위 → 집계 테이블에서 조회
```

### 콘텐츠 밀도 전략

```
문제: 홈에 "Recent Events 5건, Hot Regions 1개" — 허전
원인: 최근 30일 = GDELT(사망자0) + Wikipedia(4건) + NCTC(2건)

해결:
1. 윈도우 확대: 30일 → 90일 (Hot Regions, Recent Events)
2. GDELT 이벤트도 "사건" 섹션에 포함 (사망자 없어도)
3. Expert RSS를 "Today's Analysis" 섹션으로 홈에 표시
4. "Historical Highlight" — 37년 DB에서 오늘 날짜의 과거 사건
5. "Trend Comparison" — 이번 달 vs 작년 동기 비교
```

### 비즈니스 모델 전략

```
무료 (지금)             Pro ($50/월, Phase 3)        Enterprise (Phase 4)
─────────────────────  ───────────────────────────  ────────────────────
홈 + 지도               홈 + 지도                    전부 포함
국가 10개               국가 전체                    API 무제한
조직 10개               조직 전체                    커스텀 알림
최근 30일               37년 전체                    데이터 다운로드
일일 브리프 (Telegram)   커스텀 알림 (Telegram/Email)  전용 지원
API 100 calls/일       API 10K calls/일             SLA
─────────────────────  ───────────────────────────  ────────────────────
                       ↑ Phase 3에서 도입            ↑ Phase 4에서 도입
```

V2에서는 Pro 도입하지 않음 — 먼저 MAU 500 달성 후.
V2 목표: **사용자 경험을 완성해서 "와 이걸 무료로?" 반응 만들기**.

### 바이럴 전략

```
지금 없는 것                    V2에서 추가
─────────────────────────────  ──────────────────────────────
OG 이미지                      → 국가 카드 자동 생성 (Satori)
SNS 공유                       → "Share this country" 버튼
임베드 위젯                     → 실제 작동하는 3종 + 코드 복사
이메일 수집                     → "Get daily brief by email" 폼
Historical context             → "On this day in 2014..." 섹션
Weekly recap                   → 자동 주간 요약 페이지
```

---

## 3. V2 기능 명세

### 3.1 성능 최적화

**Pre-computed stats 테이블**:
```sql
CREATE TABLE country_stats (
  country TEXT PRIMARY KEY,
  total_events INTEGER,
  total_fatalities INTEGER,
  events_30d INTEGER,
  fatalities_30d INTEGER,
  events_90d INTEGER,
  fatalities_90d INTEGER,
  top_category TEXT,
  threat_score REAL,
  last_event_date TEXT,
  updated_at TEXT
);

CREATE TABLE org_stats (
  name TEXT PRIMARY KEY,
  total_events INTEGER,
  total_fatalities INTEGER,
  countries INTEGER,
  first_seen TEXT,
  last_seen TEXT,
  updated_at TEXT
);

CREATE TABLE global_stats (
  id INTEGER PRIMARY KEY DEFAULT 1,
  total_events INTEGER,
  total_fatalities INTEGER,
  total_countries INTEGER,
  events_7d INTEGER,
  fatalities_7d INTEGER,
  events_30d INTEGER,
  threat_index INTEGER,
  updated_at TEXT
);
```

매일 CI에서 `daily_terror.py` 실행 후 `python scripts/compute_stats.py` 실행 → 이 테이블들 갱신.

**효과**: 
- `/` 홈: 1382ms → **<10ms**
- `/countries`: 5400ms → **<50ms**  
- `/countries/Nigeria`: 15000ms → **<100ms**

### 3.2 홈 페이지 리디자인

```
┌────────────────────────────────────────────────────────────┐
│ [logo] Conflict Researcher    [search] [countries] [about] │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  GLOBAL THREAT INDEX                                       │
│  ██████████░░░░░░░░  47/100   ↑3 vs 7d avg                │
│  420K events · 2.9M killed · 161 countries · since 1989   │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                                                      │ │
│  │              WORLD MAP (full interactive)             │ │
│  │              category filters + click to navigate    │ │
│  │                                                      │ │
│  │  [1989  ──────────●──────  2026]  timeline scrubber  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────┬──────────┬──────────┬──────────┐           │
│  │💣 Terror │⚔ CivWar │🪖 War   │🔫 Cartel │           │
│  │ 27,895   │ 154,189  │ 38,773  │ 29,870   │           │
│  └──────────┴──────────┴──────────┴──────────┘           │
│                                                            │
│  ┌─────────────────────┐  ┌─────────────────────────┐    │
│  │  HOT REGIONS (90d)  │  │  TODAY'S ANALYSIS        │    │
│  │  1. Nigeria     412 │  │  [Soufan] Iran ceasefire │    │
│  │  2. Ukraine     389 │  │  [ICG] Sudan update      │    │
│  │  3. Syria       201 │  │  [CTC] ISIS recruitment  │    │
│  │  4. Mexico      187 │  │  [ISW] Ukraine frontline │    │
│  │  5. Pakistan    156 │  │                          │    │
│  └─────────────────────┘  └─────────────────────────┘    │
│                                                            │
│  RECENT EVENTS (90d, top 15)                              │
│  ... event cards with category badges ...                 │
│                                                            │
│  📜 ON THIS DAY (from 37-year archive)                    │
│  April 13, 2013: Boston Marathon bombing kills 3, injures │
│  264 (terrorism, United States)                           │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │  📨 Get the daily brief → email / Telegram          │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
├────────────────────────────────────────────────────────────┤
│ Footer                                                     │
└────────────────────────────────────────────────────────────┘
```

**새 섹션**:
1. **Today's Analysis** — expert_rss에서 오늘 수집된 4건 (소스 다양화)
2. **On This Day** — 37년 DB에서 오늘 날짜 과거 사건 1건
3. **Email subscribe** — 이메일 수집 폼 (Resend or Buttondown)
4. Threat Index **progress bar** (숫자만 → 시각적 바)
5. Hot Regions **90일 윈도우** (30일 → 90일)

### 3.3 Interactive Map (iframe 탈출)

```
방법: map-test.html의 로직을 React에 넣되,
      MapLibre를 npm 대신 window.maplibregl로 사용.

구현:
1. layout.tsx <head>에 MapLibre script 태그 (이미 CDN link 있음)
2. WorldMap.tsx에서 window.maplibregl 직접 사용
3. 카테고리 필터 React state로 관리
4. 국가 클릭 → Next.js router.push('/countries/...')
5. 타임라인 스크러버: year range slider → API refetch
```

### 3.4 검색

```
/search?q=boko+haram

검색 대상:
- 국가명 (fuzzy)
- 조직명 (fuzzy)
- 이벤트 notes (full-text)

V2: SQL LIKE (간단)
V3: Meilisearch (고급)
```

### 3.5 On This Day

```sql
SELECT date, country, actor1, fatalities, category, notes
FROM events
WHERE substr(date, 6) = '04-13'  -- 오늘 날짜의 과거 사건
  AND is_aggregate = 0
  AND fatalities >= 10
ORDER BY fatalities DESC
LIMIT 1
```

비용: 0 (DB에 이미 있음). 효과: 매일 다른 콘텐츠 → 리텐션.

### 3.6 Weekly Recap 페이지

```
/weekly/2026-W15

자동 생성:
- 이번 주 총 이벤트/사망자
- 가장 활발한 국가 top 5
- 카테고리별 분포 변화
- 가장 치명적 사건 3개
- Expert analysis 주요 5건
```

### 3.7 SNS 공유 카드 (Satori OG Image)

```
/api/og/countries/Nigeria
→ 동적 이미지 생성:

┌────────────────────────────────┐
│ 🇳🇬 Nigeria          SEVERE    │
│ 8,815 events · 81,855 killed  │
│ Top: Boko Haram, ISWAP        │
│ Conflict Researcher            │
└────────────────────────────────┘

Next.js ImageResponse API (Satori) 사용
→ OG meta에 자동 삽입
→ Twitter/Facebook 공유 시 카드 표시
```

---

## 4. V2 로드맵 (4주)

### Week 1: 성능 + 콘텐츠

| 할 일 | 효과 |
|-------|------|
| `compute_stats.py` — pre-computed 테이블 생성 | 페이지 10-100x 빨라짐 |
| 홈 쿼리를 `global_stats` 1-row lookup으로 교체 | 홈 <50ms |
| Hot Regions 90일, Recent Events 90일로 확대 | 콘텐츠 밀도 ↑ |
| "Today's Analysis" 섹션 홈에 추가 | 전문가 분석 노출 |
| "On This Day" 섹션 홈에 추가 | 매일 신규 콘텐츠 |
| 모바일 hamburger 메뉴 | 모바일 사용 가능 |

### Week 2: 인터랙티브 지도 + 검색

| 할 일 | 효과 |
|-------|------|
| WorldMap을 React 컴포넌트로 재통합 (window.maplibregl) | iframe 탈출 |
| 지도 클릭 → 국가 페이지 이동 | 탐색 흐름 완성 |
| 카테고리 필터 React state | 실시간 필터링 |
| `/search` 페이지 + SQL LIKE 검색 | 420K 이벤트 탐색 가능 |
| 국가 페이지에 활동 단체 목록 + 링크 | 콘텐츠 연결 |

### Week 3: 바이럴 엔진 + 공유

| 할 일 | 효과 |
|-------|------|
| OG Image API (Satori) — 국가 카드 자동 생성 | SNS 공유 시 카드 표시 |
| "Share this country" 버튼 (Twitter/Facebook/Copy link) | 공유 유도 |
| 위젯 쇼케이스 작동하게 수정 | 임베드 설치 유도 |
| Email subscribe 폼 (Buttondown/Resend) | 이메일 리스트 구축 |
| Weekly recap 자동 생성 (`/weekly/[week]`) | 주간 콘텐츠 |

### Week 4: 배포 + 최종 다듬기

| 할 일 | 효과 |
|-------|------|
| Vercel 배포 + 도메인 연결 | 프로덕션 라이브 |
| Turso DB 마이그레이션 (SQLite → edge) | 엣지 배포 |
| Lighthouse 90+ 최적화 | SEO + 성능 |
| 페이지별 로딩 스켈레톤 | 부드러운 UX |
| 데이터 신선도 표시 (홈 footer) | 투명성 |
| HN/Reddit 런칭 (docs/LAUNCH_POSTS.md 활용) | 초기 트래픽 |

---

## 5. V2 KPI

| 지표 | V1 (현재) | V2 목표 |
|------|----------|---------|
| 홈 페이지 속도 | 4.3초 | **<1초** |
| 국가 페이지 속도 | 15초 | **<1초** |
| Lighthouse 점수 | 미측정 | **90+** |
| 홈 콘텐츠 섹션 | 5개 | **8개** (Analysis, OnThisDay, Email 추가) |
| Recent Events | 5건 | **15건+** |
| Hot Regions | 1개 | **10개** |
| 검색 | 없음 | **있음** |
| OG Image | 없음 | **국가/조직별 자동 생성** |
| SNS 공유 | 없음 | **버튼 + 카드** |
| 이메일 구독 | 없음 | **폼 있음** |
| 위젯 작동 | 부분 | **3종 전부** |
| MAU | 0 | **100 (런칭 후 1개월)** |

---

## 6. V2 이후 로드맵

### Phase 3 (V2 + 4주): 수익화 준비

- Pro tier ($50/월) — 전체 국가, 37년 히스토리, API 10K
- Stripe 결제 연동
- 사용자 계정 (NextAuth)
- 커스텀 알림 (Telegram bot commands)

### Phase 4 (Phase 3 + 8주): 성장

- 이벤트 페이지 SEO 대량 인덱싱 (420K pages)
- Threat Wrapped (연말 리포트)
- 대학 라이선스
- 데이터 파트너십

---

## 7. 기술 결정

| 결정 | V1 | V2 |
|------|-----|-----|
| 지도 | iframe (map-test.html) | **React + window.maplibregl** |
| DB 쿼리 | 실시간 420K scan | **pre-computed stats 테이블** |
| 호스팅 | localhost | **Vercel (프로덕션)** |
| DB | 로컬 SQLite | **Turso (엣지 replica)** |
| 검색 | 없음 | **SQL LIKE → Phase 3에서 Meilisearch** |
| OG Image | 없음 | **Satori (Next.js ImageResponse)** |
| 이메일 | 없음 | **Buttondown (무료 티어)** |
| 공유 | 없음 | **Web Share API + fallback** |

---

*V2 Plan v1 | 2026-04-13 | Conflict Researcher*
