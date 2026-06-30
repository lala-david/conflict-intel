# 무료 클라우드 배포 가이드 (Turso + GitHub Actions + Cloudflare Pages)

로컬 Windows 예약작업을 대체해 **전부 무료 클라우드**에서 매일 자동 수집 + 항상 켜진 사이트를 운영합니다.

```
[GitHub Actions cron]  ──매일──▶  파이프라인 수집  ──▶  terror.db (GitHub Release 보관)
                                        │
                                        └─변경분 동기화─▶  [Turso 클라우드 SQLite]
                                                                   ▲
                                                          읽기      │
                                                [Cloudflare Pages = 정식 사이트]
```

코드/설정은 **이미 다 준비**되어 있습니다. 아래는 **계정 생성·시크릿 등록 등 직접 해야 하는 부분**입니다.

---

## 사전 준비: 현재 상태
- 웹 데이터 레이어는 `@libsql/client`(Turso 호환)로 전환 완료 — `npm run build` 통과
- `TURSO_DATABASE_URL` 미설정 시 로컬 `data/terror.db` 파일을 그대로 읽음(개발용)
- 파이프라인(`scripts/daily_terror.py`)은 변경 없이 로컬 sqlite 에 기록
- `scripts/export_for_turso.py` 가 변경분을 Turso 동기화 SQL 로 출력

---

## 1단계 — Turso (클라우드 SQLite, 무료)

```bash
# 설치 (Windows는 WSL 또는 Git Bash 권장)
curl -sSfL https://get.tur.so/install.sh | bash
turso auth signup            # 브라우저로 가입 (GitHub 계정 가능)

# DB 생성
turso db create terror
turso db show terror --url               # → TURSO_DATABASE_URL (libsql://terror-xxxx.turso.io)
turso db tokens create terror            # → TURSO_AUTH_TOKEN (사이트 읽기용)
turso auth api-tokens create ci          # → TURSO_API_TOKEN (Actions CLI 인증용)

# 기존 데이터 전체를 Turso로 1회 마이그레이션 (419K건, 수 분 소요)
python scripts/export_for_turso.py --full > turso_full.sql
turso db shell terror < turso_full.sql
```

> 검증: `turso db shell terror "SELECT total_events,total_countries FROM global_stats"`
> → `419381 | 170` 처럼 나오면 성공.

---

## 2단계 — GitHub repo 시크릿/변수 등록

GitHub repo → **Settings → Secrets and variables → Actions**

**Secrets** (New repository secret):
| 이름 | 값 |
|------|----|
| `OPENAI_API_KEY` | 기존 OpenAI 키 (.env 참고) |
| `UCDP_TOKEN` | 기존 UCDP 토큰 (.env 참고) |
| `TURSO_API_TOKEN` | 위 `turso auth api-tokens create ci` 결과 |

**Variables** (Variables 탭 → New repository variable):
| 이름 | 값 |
|------|----|
| `TURSO_DB_NAME` | `terror` |

> 워크플로(`.github/workflows/daily-terror.yml`)는 이미 cron(매일 09:00 KST) + Turso 동기화 + Release DB 영속화로 구성됨.
> 등록 후 **Actions 탭 → Daily Terror Intelligence → Run workflow** 로 수동 1회 실행해 검증.

---

## 3단계 — Cloudflare Pages (정식 사이트, 무료)

1. [Cloudflare 가입](https://dash.cloudflare.com) → **Workers & Pages → Create → Pages → Connect to Git**
2. `terror_researcher` repo 연결, **Root directory = `web`**
3. 빌드 설정:
   - Framework preset: **Next.js**
   - Build command: `npx @cloudflare/next-on-pages@1`
   - Build output directory: `.vercel/output/static`
4. **환경변수** (Settings → Environment variables, Production):
   | 이름 | 값 |
   |------|----|
   | `TURSO_DATABASE_URL` | `libsql://terror-xxxx.turso.io` |
   | `TURSO_AUTH_TOKEN` | 1단계 `turso db tokens create terror` 결과 |
   | `NODE_VERSION` | `20` |
5. Deploy.

> ⚠️ **엣지 런타임 마무리 작업**: Cloudflare Pages(Workers 런타임)에서 동적 라우트는
> `export const runtime = 'edge'` 가 필요하고, `db.ts` 의 import 를 `@libsql/client/web` 로
> 바꿔야 할 수 있습니다. 이 부분은 **첫 배포 빌드 로그를 보고 함께 마무리**하는 게 가장 확실합니다.
> (계정 연결 후 알려주시면 제가 엣지 대응 커밋을 만들어 드립니다.)

---

## 4단계 — 검증 체크리스트
- [ ] `turso db shell terror "SELECT COUNT(*) FROM events"` → 419,000+ 건
- [ ] GitHub Actions 수동 실행 성공 (녹색) + `db-latest` Release 에 terror.db 업로드됨
- [ ] Cloudflare Pages 사이트 접속 → 홈 통계가 Turso 값과 일치
- [ ] 다음날 09:00 KST 자동 실행 확인

---

## 롤백 / 참고
- 로컬 개발은 그대로: `cd web && npm run dev` (Turso 환경변수 없으면 로컬 DB 사용)
- 로컬 예약작업은 더 이상 불필요 → 비활성화 권장:
  `Disable-ScheduledTask -TaskName "TerrorDailyReport"`
- 정리 전 DB 백업: `data/terror.db.bak`
