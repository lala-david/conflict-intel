"""
Connector registry — the single place that declares every data source.

Adding a source = add one line here. Each entry adapts an existing collector
into the uniform Connector interface, so Bronze/Silver/Gold treat them alike.
The `key` matches the dict key that the Silver transform expects.

NCTC runs once a day (17:00 KST) — the daily workflow sets RUN_NCTC=skip on the
other cycles so it's excluded there. Unset (local/manual runs) includes it.
"""
import os
from datetime import datetime

from pipeline.base import Connector, FnConnector


def build_registry(target_date: datetime) -> list[Connector]:
    from sources import (
        fetch_gdelt,
        fetch_ucdp,
        fetch_google_news,
        fetch_expert_rss,
        fetch_sanctions_updates,
        fetch_ofac_recent,
        fetch_wikipedia_incidents,
    )
    from nctc_source import fetch_nctc_daily
    from telegram_source import fetch_telegram
    from config import TELEGRAM_CHANNELS

    connectors: list[Connector] = [
        FnConnector("gdelt", fetch_gdelt, target_date),
        FnConnector("ucdp", fetch_ucdp, target_date),
        FnConnector("google_news", fetch_google_news),
        FnConnector("expert_rss", fetch_expert_rss),
        FnConnector("sanctions", fetch_sanctions_updates),
        FnConnector("ofac", fetch_ofac_recent),
        FnConnector("wikipedia", fetch_wikipedia_incidents),
        FnConnector("nctc", fetch_nctc_daily, 5),
        FnConnector("telegram", fetch_telegram, TELEGRAM_CHANNELS),
    ]
    # NCTC only on its once-a-day (17:00 KST) run; skipped on the other cycles.
    if os.environ.get("RUN_NCTC") == "skip":
        connectors = [c for c in connectors if c.name != "nctc"]
    return connectors
