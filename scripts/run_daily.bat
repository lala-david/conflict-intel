@echo off
setlocal
cd /d C:\Users\강성준\Desktop\app\terror

set "TS=%date:~0,4%-%date:~5,2%-%date:~8,2%"
set "LOG=logs\run_daily_%TS%.log"
if not exist logs mkdir logs

echo === %TS% %time% === >> "%LOG%"
python scripts\pipeline\run.py >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [ERROR] pipeline/run.py failed >> "%LOG%"
    exit /b 1
)

git add reports\ data\classifications.json data\conflict_zones.json data\countries.json data\organizations.json data\.sanctions_cache.json data\known_ucdp_ids.json >> "%LOG%" 2>&1
git diff --staged --quiet || (git commit -m "intel: %TS% daily brief" >> "%LOG%" 2>&1 && git push >> "%LOG%" 2>&1)
echo === done %time% === >> "%LOG%"
endlocal
