# Terror Researcher

자동화된 일일 테러/분쟁 인텔리전스 시스템.

6개 데이터 소스를 매일 자동 수집 → 정제 → 교차검증 → 분석 → 보고서 생성.

## 데이터 소스

| 소스 | 유형 | 데이터 |
|------|------|--------|
| GDELT | 미디어 이벤트 | CAMEO 코드 기반 분쟁/테러 이벤트 |
| UCDP | 분쟁 사건 DB | 사상자 포함 코딩된 분쟁 사건 |
| Google News | 뉴스 검색 | 8개 테러 관련 검색어 RSS |
| Expert RSS | 전문가 피드 | 17개 기관 (ISW, CTC, Soufan 등) |
| OpenSanctions | 제재 목록 | UN/US/EU 제재 대상 변동 감지 |
| OFAC | 미 재무부 | 최근 제재 조치 |

## 분석 파이프라인

```
수집(병렬) → 조직/국가/분쟁지역 매칭 → 뉴스 클러스터링 → 위협도/핫스팟 분석 → 보고서 생성
```

## 보고서 구조

- **BLUF**: 3~5줄 핵심 요약 (유일한 LLM 사용, ~600 토큰/일)
- 수집 통계, 위협 수준, 지역별 분석
- UCDP 주요 사건 (사상자 포함)
- GDELT 미디어 이벤트
- 뉴스 클러스터, 조직 동향, 핫스팟
- 제재 동향, 전문가 분석

## 설치

```bash
pip install -r requirements.txt
```

## 환경 변수 (.env)

```
OPENAI_API_KEY=your-key    # BLUF 생성용
UCDP_TOKEN=your-token      # UCDP API (https://ucdp.uu.se/apidocs/)
```

## 실행

```bash
# 오늘 보고서
python scripts/daily_terror.py

# 특정 날짜
python scripts/daily_terror.py 2026-04-07

# 주간 요약
python scripts/weekly_summary.py
```

## 참조 데이터

| 파일 | 내용 | 규모 |
|------|------|------|
| organizations.json | 제재 대상 + 무장단체 | 286 조직, 341 인물 |
| countries.json | 국가별 위협도/활동단체 | 172개국 |
| conflict_zones.json | 분쟁지역 좌표 | 71개 zone |
| classifications.json | 공격/표적/무기 분류 체계 | 33 카테고리 |

## CI/CD

GitHub Actions: 매일 UTC 06:00 (KST 15:00) 자동 실행
- 데이터 수집 → 보고서 생성 → git commit/push
- 일요일: 주간 요약 추가 생성
- 실패 시 GitHub Issue 자동 생성
