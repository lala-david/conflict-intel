# Conflict Researcher — Business Model

> 2026-04-13 | 수익화 전략 + 기능 게이팅 설계

---

## 1. 핵심 인사이트

### 우리가 가진 것
- **420K 이벤트, 37년, 161개국** — 돈으로 못 사는 역사 데이터
- **10 카테고리 학계 분류** — 경쟁사에 없는 정직한 분류
- **8개 소스 일일 자동 수집** — 인건비 0
- **$1/월 운영비** — 극도로 낮은 고정비

### 누가 돈을 낼까 (검증 필요)

| Persona | 고통 | 지불 의사 | 우선순위 |
|---------|------|----------|---------|
| **보안 컨설턴트** | 클라이언트 브리핑에 신뢰할 데이터 필요 | $50-200/월 | 1순위 |
| **NGO 현장팀** | 활동 지역 리스크 모니터링 | $20-50/월 | 2순위 |
| **대학 연구자** | GTD 중단 후 대안 필요 | $500-2K/년 | 3순위 |
| **여행 리스크 스타트업** | API로 국가별 위협도 | $200-2K/월 | 4순위 |
| **보험 언더라이터** | 정치적 리스크 정량 데이터 | 협의 | 5순위 |

---

## 2. 3-Tier 모델

### Free (지금)
**목적**: 사용자 획득 + 바이럴

| 기능 | 포함 |
|------|------|
| 홈 대시보드 (지도, 카테고리, 핫스팟) | ✅ |
| 국가 페이지 (상위 30개국) | ✅ |
| 조직 페이지 (상위 20개) | ✅ |
| 일일 브리프 (Telegram + 웹) | ✅ |
| 최근 90일 이벤트 | ✅ |
| 검색 (기본) | ✅ |
| 임베드 위젯 3종 | ✅ |
| API: 100 calls/일 | ✅ |

**제한**:
- 국가 상세: 상위 30개국만 (나머지 "Unlock with Pro")
- 조직 상세: 상위 20개만
- 타임라인: 최근 5년만 (37년 전체는 Pro)
- CSV 다운로드: 불가
- 이벤트 상세: 최근 1년만

### Pro ($29/월 or $249/년)
**목적**: 개인 분석가, 프리랜서, 소규모 컨설턴트

| 기능 | 포함 |
|------|------|
| 모든 국가 (161개) 상세 | ✅ |
| 모든 조직 (289개) 상세 | ✅ |
| 37년 전체 타임라인 | ✅ |
| 전체 이벤트 상세 (420K) | ✅ |
| CSV 다운로드 (국가/조직별) | ✅ |
| 커스텀 Telegram 알림 | ✅ |
| 이메일 Morning Brief | ✅ |
| Weekly Recap | ✅ |
| API: 10K calls/일 | ✅ |
| 광고/위젯 "Powered by" 제거 | ✅ |

**가격 근거**:
- Janes: $150K/년 (100x 비쌈)
- Recorded Future: $100K/년
- ACLED 상업 라이선스: 협의 (보통 $10K+)
- **우리: $249/년** → 1/400 가격. 소규모 컨설턴트도 부담 없음

### Team ($99/월 or $899/년)
**목적**: NGO, 소규모 보안 회사, 연구소

| 기능 | 포함 |
|------|------|
| Pro 전체 | ✅ |
| 팀 5명까지 | ✅ |
| 커스텀 대시보드 (국가/지역 고정) | ✅ |
| API: 100K calls/일 | ✅ |
| Slack/Discord 웹훅 알림 | ✅ |
| 우선 지원 | ✅ |

### Enterprise (협의)
**목적**: 보험사, 대기업, 정부기관

- 전용 DB 인스턴스
- SLA
- 커스텀 데이터 피드
- 온프레미스 배포 옵션

---

## 3. 수익 시나리오

### 보수적 (12개월 후)
```
Free: 2,000 MAU (변환률 2%)
Pro: 40명 × $29/월 = $1,160/월
Team: 3팀 × $99/월 = $297/월
────────────────────────
MRR: $1,457 (~$17.5K ARR)
운영비: $20/월
순이익: $1,437/월
```

### 낙관적 (12개월 후)
```
Free: 5,000 MAU (변환률 3%)
Pro: 150명 × $29/월 = $4,350/월
Team: 10팀 × $99/월 = $990/월
────────────────────────
MRR: $5,340 (~$64K ARR)
```

### 손익분기
**Pro 1명** ($29/월) > 운영비 ($20/월) → **1명이면 흑자**

---

## 4. 기능 게이팅 구현

### 프론트엔드 게이팅 (Phase 3에서 구현)

```typescript
// lib/access.ts
type Tier = 'free' | 'pro' | 'team';

const FREE_COUNTRIES = 30;  // top 30 by fatalities
const FREE_ORGS = 20;
const FREE_YEARS = 5;       // 2021-2026
const FREE_API_DAILY = 100;

export function canAccessCountry(country: string, tier: Tier): boolean {
  if (tier !== 'free') return true;
  // Check if country is in top 30
  return isTopCountry(country, FREE_COUNTRIES);
}

export function canAccessFullTimeline(tier: Tier): boolean {
  return tier !== 'free';
}

export function canDownloadCSV(tier: Tier): boolean {
  return tier !== 'free';
}
```

### Phase 3에서 구현할 것
1. NextAuth (Google + GitHub 로그인)
2. Stripe 결제 연동
3. 기능 게이팅 미들웨어
4. 사용량 추적 (API calls)
5. Pricing 페이지

### 지금 (V2에서) 준비할 것
1. **Pricing 페이지** — 아직 결제 안 받지만 "Coming Soon"으로 노출
2. **기능 게이트 UI** — "Unlock with Pro" 배너 (클릭 시 Pricing 이동)
3. **이메일 수집** — "Get notified when Pro launches" 폼

---

## 5. 바이럴 엔진 (무료 성장)

| 엔진 | 구현 | 예상 효과 |
|------|------|----------|
| **임베드 위젯** | ✅ 있음 | 뉴스사이트에서 무료 노출 |
| **OG 카드** | ✅ 있음 | SNS 공유 시 카드 표시 |
| **공유 버튼** | ✅ 있음 | 국가 페이지 공유 유도 |
| **On This Day** | ✅ 있음 | 매일 다른 콘텐츠 |
| **Weekly Recap** | 🔨 만들 것 | 주간 바이럴 콘텐츠 |
| **이벤트 페이지 SEO** | ✅ 있음 | 구글 유기 트래픽 |
| **Telegram 채널** | ✅ 있음 | 일일 리텐션 |
| **이메일 리스트** | 🔨 만들 것 | 직접 도달 |

---

## 6. 경쟁 포지셔닝

```
가격 ←──────────────────────────────→ 기능
$0                                    Full
│                                      │
│  Conflict Researcher (Free)          │
│  ├── 지도, 검색, 카테고리             │
│  └── 30개국, 20조직, 5년             │
│                                      │
│     Conflict Researcher (Pro $29)    │
│     ├── 전체 데이터                   │
│     └── CSV, API, 알림              │
│                                      │
│                          ACLED ($10K+)
│                          Janes ($150K)
│                          Recorded Future ($100K+)
```

**핵심 메시지**: "Janes가 하는 일을 1/5000 가격에"

---

*Business Model v1 | 2026-04-13*
