@echo off
cd /d C:\Users\강성준\Desktop\app\terror
python scripts/daily_terror.py
git add -A
git diff --staged --quiet || (git commit -m "report: %date:~0,4%-%date:~5,2%-%date:~8,2% daily brief" && git push)
