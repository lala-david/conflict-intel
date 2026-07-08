"""
Show waitlist / demand-capture signups from Cloudflare D1.

  CLOUDFLARE_ACCOUNT_ID=... CLOUDFLARE_API_TOKEN=... D1_DATABASE_ID=... \
      python scripts/view_waitlist.py

(Same three vars the daily sync uses — see scripts/sync_to_d1.py.)
"""
import os
import sys
import requests

acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
tok = os.environ.get("CLOUDFLARE_API_TOKEN", "")
dbid = os.environ.get("D1_DATABASE_ID", "")
if not (acct and tok and dbid):
    sys.exit("Set CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN and D1_DATABASE_ID env vars.")

api = f"https://api.cloudflare.com/client/v4/accounts/{acct}/d1/database/{dbid}/query"
r = requests.post(
    api,
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    json={"sql": "SELECT created_at, email, interest, source FROM waitlist "
                 "ORDER BY created_at DESC LIMIT 1000"},
    timeout=60,
)
body = r.json()
if not body.get("success", False):
    sys.exit("D1 error: " + str(body.get("errors")))

rows = body["result"][0]["results"]
print(f"{len(rows)} signup(s):\n")
by_interest: dict[str, int] = {}
for row in rows:
    created = row.get("created_at") or ""
    email = row.get("email") or ""
    interest = row.get("interest") or ""
    source = row.get("source") or ""
    by_interest[interest] = by_interest.get(interest, 0) + 1
    print(f"  {created[:16]}  {email:35}  {interest:8}  {source}")
print("\nby interest:", by_interest)
