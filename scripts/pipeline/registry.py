"""
Connector registry — the single place that declares every data source.

Adding a source = add one line here. Each entry adapts an existing collector
into the uniform Connector interface, so Bronze/Silver/Gold treat them alike.
The `key` matches the dict key that the Silver transform expects.
"""
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

    return [
        FnConnector("gdelt", fetch_gdelt, target_date),
        FnConnector("ucdp", fetch_ucdp, target_date),
        FnConnector("google_news", fetch_google_news),
        FnConnector("expert_rss", fetch_expert_rss),
        FnConnector("sanctions", fetch_sanctions_updates),
        FnConnector("ofac", fetch_ofac_recent),
        FnConnector("wikipedia", fetch_wikipedia_incidents),
        FnConnector("nctc", fetch_nctc_daily, 1),
        FnConnector("telegram", fetch_telegram, TELEGRAM_CHANNELS),
    ]
