<#
  로컬(노트북) 백필 러너 — CI 가 D1 용량 초과로 죽어 있는 동안 gap 기간의
  데이터를 이 노트북에서 채운다.

  CI 는 2026-08-03 이후 매 런이 'Sync to D1' 에서 죽었고, 그 스텝 뒤에 있는
  DB 캐시 저장 / db-latest 갱신 / 리포트 커밋이 전부 스킵됐다. 즉 수집은 했지만
  결과가 하나도 남지 않았다. 그래서 여기서 다시 수집한다.

    .\scripts\run_backfill_local.ps1                      # 상태파일 이어서 ~ 오늘
    .\scripts\run_backfill_local.ps1 -From 2026-08-04     # 시작일 지정
    .\scripts\run_backfill_local.ps1 -From 2026-08-04 -To 2026-08-10
    .\scripts\run_backfill_local.ps1 -Reset               # 상태 버리고 -From 부터
    .\scripts\run_backfill_local.ps1 -Fast                # LLM 정제 생략 (아래)

  하루씩 돌고 data\backfill_state.json 에 진행 상황을 남기므로 중간에 창을 닫아도
  다시 실행하면 이어서 간다. 로그는 logs\backfill_local_<날짜>.log (UTF-8).

  속도: 기본은 하루 ~15분 (LAN gemma 의 actor 채우기 + LLM dedup 이 대부분).
  -Fast 는 그 두 단계를 빼서 하루 ~1분으로 줄인다 — 56일이면 14시간 vs 1시간.
  빠진 정제는 원본 행이 이미 저장된 뒤에 얹는 것이라, 범위를 다 채우고
  scripts\full_dedup_chunked.py 같은 벌크 패스를 한 번 돌리면 결과가 같아진다.

  D1 동기화는 일부러 하지 않는다 — D1 이 무료 한도(500MB)를 넘겨 INSERT 가
  code 7500 "Exceeded maximum DB size" 로 거부되는 상태다. 용량 문제를 정리한 뒤
  scripts\sync_to_d1.py 를 따로 돌려야 사이트에 반영된다.
#>
[CmdletBinding()]
param(
    [string]$From = "2026-08-04",
    [string]$To   = "",
    [switch]$Reset,
    [switch]$Fast
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "logs")) { New-Item -ItemType Directory "logs" | Out-Null }
$script:log = Join-Path $root ("logs\backfill_local_{0:yyyy-MM-dd}.log" -f (Get-Date))
$state = "data\backfill_state.json"
$lock  = "data\backfill.lock"

# PS 5.1 의 Tee-Object/Out-File 기본 인코딩은 UTF-16 이라 로그가 읽히지 않는다.
# 콘솔에 그대로 보여주면서 파일에는 UTF-8 로 붙인다.
function Write-Log {
    param([Parameter(ValueFromPipeline = $true)][string]$Line)
    process {
        Write-Host $Line
        Add-Content -Path $script:log -Value $Line -Encoding utf8
    }
}

# 두 런이 같은 SQLite 파일을 동시에 쓰면 'database is locked' 로 그 날이 통째로
# 날아간다. 살아 있는 PID 가 잡고 있으면 새로 시작하지 않는다.
if (Test-Path $lock) {
    $held = (Get-Content $lock -Raw).Trim()
    if ($held -and (Get-Process -Id ([int]$held) -ErrorAction SilentlyContinue)) {
        Write-Host "another backfill is already running (PID $held) — exiting."
        Write-Host "정말 멈췄다면: Remove-Item $lock"
        exit 1
    }
    Remove-Item $lock -Force
}
$PID | Set-Content $lock -Encoding ascii

try {
    # BACKFILL_ONLY: 과거 날짜를 존중하는 소스(gdelt, ucdp)만 돌린다. 나머지는 실시간
    # 피드라서 백필 하루마다 '오늘' 것을 다시 긁어올 뿐이다 (scripts\pipeline\registry.py).
    $env:BACKFILL_ONLY = "1"
    $env:PYTHONUNBUFFERED = "1"
    if ($Fast) { $env:SKIP_LLM = "1" } else { $env:SKIP_LLM = "" }

    $today = (Get-Date).Date
    $start = [datetime]::ParseExact($From, "yyyy-MM-dd", $null)
    if ($To) { $end = [datetime]::ParseExact($To, "yyyy-MM-dd", $null) } else { $end = $today }
    # 미래 날짜는 아카이브가 없어 GDELT 가 조용히 며칠 전으로 떨어진다 — 잘라낸다.
    if ($end -gt $today) {
        Write-Host "-To $($end.ToString('yyyy-MM-dd')) is in the future — clamped to today"
        $end = $today
    }
    if ($start -gt $today) { throw "-From $From is in the future" }

    if ((-not $Reset) -and (Test-Path $state)) {
        $done = (Get-Content $state -Raw | ConvertFrom-Json).last_done
        if ($done) {
            $resume = ([datetime]::ParseExact($done, "yyyy-MM-dd", $null)).AddDays(1)
            if ($resume -gt $start) {
                Write-Host "resuming after $done"
                $start = $resume
            }
        }
    }

    $total = [int](($end - $start).TotalDays) + 1
    if ($total -le 0) {
        Write-Host "nothing to do — $($start.ToString('yyyy-MM-dd')) is past $($end.ToString('yyyy-MM-dd'))"
        exit 0
    }

    $mode = "full"
    if ($Fast) { $mode = "fast (SKIP_LLM)" }
    "=== backfill $($start.ToString('yyyy-MM-dd')) .. $($end.ToString('yyyy-MM-dd')) ($total days, $mode) @ $(Get-Date -Format s) ===" | Write-Log

    $i = 0
    $failed = @()
    for ($d = $start; $d -le $end; $d = $d.AddDays(1)) {
        $ds = $d.ToString("yyyy-MM-dd")
        $i++
        $t0 = Get-Date
        "--- [$i/$total] $ds ---" | Write-Log
        python -u scripts\pipeline\run.py $ds 2>&1 | Write-Log
        if ($LASTEXITCODE -ne 0) {
            # 하루 실패로 전체를 멈추지 않는다 (아카이브 구멍 등) — 끝에 모아서 보고.
            "  [WARN] $ds failed (exit $LASTEXITCODE) — continuing" | Write-Log
            $failed += $ds
        }
        "  [$ds took $([int]((Get-Date) - $t0).TotalSeconds)s]" | Write-Log
        # 실패한 날도 last_done 으로 기록한다 — 재실행이 같은 구멍에 다시 걸려 멈추지
        # 않게. 못 채운 날은 아래 목록으로 남으니 필요하면 -From 으로 골라 다시 돈다.
        @{ last_done = $ds } | ConvertTo-Json | Set-Content $state -Encoding utf8
    }

    "=== post-processing ===" | Write-Log
    # crypto 는 날짜를 안 받는 실시간 피드 묶음이라 백필 하루하루 돌릴 이유가 없다
    # (graphsense 가 tagpack .yaml 을 하나씩 받아서 혼자 ~13분). 범위 끝에 한 번만.
    "--- crypto (once) ---" | Write-Log
    python -u scripts\pipeline\crypto.py 2>&1 | Write-Log
    "--- normalize_countries ---" | Write-Log
    python -u scripts\normalize_countries.py 2>&1 | Write-Log
    "--- compute_stats ---" | Write-Log
    python -u scripts\compute_stats.py 2>&1 | Write-Log

    "=== done @ $(Get-Date -Format s) — $($total - $failed.Count)/$total days ok ===" | Write-Log
    if ($failed.Count) { "failed days: $($failed -join ', ')" | Write-Log }

    Write-Host ""
    if ($Fast) {
        Write-Host "-Fast was used — the LLM refinement pass still has to run:"
        Write-Host "  python scripts\full_dedup_chunked.py    (bulk LLM dedup)"
        Write-Host ""
    }
    Write-Host "D1 sync was NOT run — D1 is over its 500MB free-tier limit (code 7500)."
    Write-Host "Fix the size first, then: python scripts\sync_to_d1.py"
    Write-Host "log: $script:log"
}
finally {
    Remove-Item $lock -Force -ErrorAction SilentlyContinue
}
