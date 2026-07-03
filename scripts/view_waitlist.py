"""
Show waitlist / demand-capture signups from Turso.

  TDB=libsql://<db>.turso.io TTOK=<token> python scripts/view_waitlist.py

(TDB/TTOK are the same Turso URL + auth token used by load_turso.py.)
"""
import os
import sys
import requests

url = os.environ.get("TDB", "")
tok = os.environ.get("TTOK", "")
if not url or not tok:
    sys.exit("Set TDB (libsql url) and TTOK (auth token) env vars.")

endpoint = url.replace("libsql://", "https://").rstrip("/") + "/v2/pipeline"
r = requests.post(
    endpoint,
    headers={"Authorization": f"Bearer {tok}"},
    json={"requests": [
        {"type": "execute", "stmt": {"sql":
            "SELECT created_at, email, interest, source FROM waitlist ORDER BY created_at DESC LIMIT 1000"}},
        {"type": "close"},
    ]},
    timeout=60,
)
res = r.json()["results"][0]
if res.get("type") == "error":
    sys.exit("Turso error: " + res["error"]["message"])

rows = res["response"]["result"]["rows"]
print(f"{len(rows)} signup(s):\n")
by_interest: dict[str, int] = {}
for row in rows:
    created, email, interest, source = (c.get("value", "") for c in row)
    by_interest[interest] = by_interest.get(interest, 0) + 1
    print(f"  {created[:16]}  {email:35}  {interest:8}  {source}")
print("\nby interest:", by_interest)
