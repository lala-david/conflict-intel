# 무료 클라우드 배포 가이드 (Cloudflare D1 + GitHub Actions + Cloudflare Workers)

로컬 Windows 예약작업을 대체해 **전부 무료 클라우드**에서 매일 자동 수집 + 항상 켜진 사이트를 운영합니다.

```
[GitHub Actions cron]  ──매일──▶  파이프라인 수집  ──▶  conflict.db (GitHub Release 보관)
                                        │
                                        └─변경분 동기화─▶  [Cloudflare D1 (SQLite)]
                                                                   ▲
                                                          읽기      │  (D1 바인딩, 외부 서비스 없음)
                                                [Cloudflare Worker = 정식 사이트]
```

데이터 백엔드는 **Cloudflare D1**(Cloudflare 네이티브 SQLite)입니다. 별도 호스팅 DB·인증
토큰 없이 Worker에 `DB` 바인딩으로 직접 붙고, 무료 티어(5GB 저장 / 하루 500만 row-read)
안에서 동작합니다. 코드/설정은 **이미 다 준비**되어 있고, 아래는 **계정 생성·시크릿 등록 등
직접 해야 하는 부분**입니다.

---

## 0단계 — Docker 셀프호스트 (가장 간단, 클라우드 불필요)

집/서버 어디서든 Docker만 있으면 바로 돕니다:

```bash
git clone https://github.com/lala-david/conflict-intel.git && cd terror_researcher
cp .env.example .env                                            # OPENAI_API_KEY, UCDP_TOKEN
gh release download db-latest --pattern conflict.db --dir data   # 기존 DB 시드(선택)

docker compose run --rm pipeline     # 1회 수집 (bronze → silver → gold)
docker compose up -d scheduler       # 매일 자동 수집 (상시)
cd web && npm install && npm run dev  # 대시보드
```

`data/`(conflict.db + bronze Parquet)와 `reports/`는 볼륨으로 영속됩니다.
아래 D1/Cloudflare 단계는 **공개 클라우드 사이트**를 운영할 때만 필요합니다.

---

## 사전 준비: 현재 상태
- 웹 데이터 레이어(`web/lib/db.ts`)는 **Cloudflare D1** 바인딩(`DB`)을 읽음 — `npm run build` 통과
- Workers 밖(로컬 `npm run dev` / 빌드)에서는 `better-sqlite3`로 `data/conflict.db`를 직접 읽음
  (better-sqlite3는 external 처리되어 Worker 번들에 안 들어감 — `web/next.config.mjs`)
- 파이프라인(`scripts/pipeline/run.py`, 메달리온 Bronze/Silver/Gold)이 로컬 sqlite + Parquet(bronze) 에 기록
- `scripts/sync_to_d1.py` 가 변경분을 D1 HTTP API로 동기화 (events append + stats 전체교체, 안전가드 내장)

---

## 1단계 — Cloudflare D1 (SQLite, 무료)

```bash
cd web
npx wrangler login                         # 브라우저로 Cloudflare 로그인

# D1 DB 생성 → 출력된 database_id 를 web/wrangler.jsonc 의
#   "database_id": "REPLACE_WITH_D1_DATABASE_ID" 자리에 붙여넣기
npx wrangler d1 create conflict-intel

# 기존 데이터 전체(스키마+인덱스+행)를 D1 로 1회 적재 (벌크, wrangler 가 자동 배치)
cd ..
python scripts/dump_for_d1.py                       # → data/conflict_d1.sql (~255MB)
cd web
npx wrangler d1 execute conflict-intel --remote --yes --file=../data/conflict_d1.sql

# 사이트 전용 waitlist 테이블 1회 생성 (conflict.db 에는 없는 앱 테이블)
npx wrangler d1 execute conflict-intel --remote --yes --file=../scripts/d1_waitlist_schema.sql
```

> 검증: `npx wrangler d1 execute conflict-intel --remote \
>   --command "SELECT total_events,total_countries FROM global_stats"`
> → `570000+ | 255` 처럼 나오면 성공.

> `d1 execute --file` 은 대용량도 wrangler 가 알아서 청크로 나눠 실행합니다(수십초~수분).
> wrangler 없이 REST 로만 초기 적재하려면(느림): `sync_to_d1.py --full` (2단계 시크릿 필요).

---

## 2단계 — GitHub repo 시크릿 등록

GitHub repo → **Settings → Secrets and variables → Actions → Secrets** (New repository secret):

| 이름 | 값 |
|------|----|
| `OPENAI_API_KEY` | 기존 OpenAI 키 (.env 참고) |
| `UCDP_TOKEN` | 기존 UCDP 토큰 (.env 참고) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 대시보드 우측 Account ID (또는 `wrangler whoami`) |
| `CLOUDFLARE_API_TOKEN` | My Profile → API Tokens → **D1 Edit** 권한 토큰 |
| `D1_DATABASE_ID` | 1단계 `wrangler d1 create` 가 출력한 database_id |

> 워크플로(`.github/workflows/daily-terror.yml`)는 이미 cron(하루 3회, 09/14/19 KST) +
> D1 동기화(`scripts/sync_to_d1.py`) + Release DB 영속화로 구성됨.
> 등록 후 **Actions 탭 → Daily Conflict Intelligence → Run workflow** 로 수동 1회 실행해 검증.

---

## 3단계 — Cloudflare Worker 배포 (정식 사이트, 무료)

이 앱은 **OpenNext**(`@opennextjs/cloudflare`)로 Cloudflare Workers 에 배포됩니다.
`web/wrangler.jsonc` 의 `d1_databases` 바인딩(`DB`)이 1단계 D1 을 가리키면 됩니다.

```bash
cd web
# wrangler.jsonc 의 database_id 가 실제 값으로 채워졌는지 먼저 확인
npm install
npx wrangler login          # (1단계에서 이미 했으면 생략)
npm run cf:deploy           # Linux/CI: opennextjs build + deploy
# Windows: npm run cf:deploy:win  (아래 참고)
```

> ⚠️ **Windows 로컬 배포**: `opennextjs-cloudflare deploy`(및 wrangler 의 OpenNext
> 프레임워크 훅)는 Windows 에서 `open-next.config.ts` 를 `C:\` 절대경로로 import 하다
> `ERR_UNSUPPORTED_ESM_URL_SCHEME` 로 죽습니다. 그래서 `npm run cf:deploy:win`
> (`web/deploy-win.mjs`)이 대신 **빌드 → config 잠시 숨김 → `wrangler deploy` → 복원**
> 순으로 동작합니다. 빌드된 워커 자체는 정상이라 이 우회로 문제없이 배포됩니다.
> (Linux/CI 에서는 `npm run cf:deploy` 를 그대로 쓰세요.)

- 로컬 프리뷰(로컬 D1 대신 실 D1 바인딩으로 확인하려면): `npm run cf:preview`
- 대시보드 변수(dashboard vars)는 `wrangler deploy` 시 덮어써지므로, **모든 설정은
  `wrangler.jsonc` 에 둡니다** (D1 바인딩 포함). 대시보드에서 수동 추가 금지.

---

## 4단계 — 검증 체크리스트
- [ ] `wrangler d1 execute conflict-intel --remote --command "SELECT COUNT(*) FROM events"` → 590,000+ 건
- [ ] GitHub Actions 수동 실행 성공(녹색) + `db-latest` Release 에 conflict.db 업로드됨
- [ ] 배포된 Worker 사이트 접속 → 홈 통계가 D1 값과 일치
- [ ] 다음날 09:00 KST 자동 실행 확인

---

## 롤백 / 참고
- 로컬 개발은 그대로: `cd web && npm run dev` (D1 바인딩 없으면 `data/conflict.db` 직접 사용)
- 로컬 예약작업은 더 이상 불필요 → 비활성화 권장:
  `Disable-ScheduledTask -TaskName "TerrorDailyReport"`
- 정리 전 DB 백업: `data/conflict.db.bak`
