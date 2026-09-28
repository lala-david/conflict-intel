@echo off
REM CI가 D1 용량 초과로 멈춘 구간(2026-08-04~)을 이 노트북에서 백필.
REM 더블클릭하면 끝까지 돕니다 (재개 가능). 창을 닫으면 멈추니 그냥 두세요.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_backfill_local.ps1" %*
pause
