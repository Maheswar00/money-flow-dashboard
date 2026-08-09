from datetime import datetime

import streamlit as st

# One cached "marker" per cache tier used across utils/data_loader.py,
# utils/cot_loader.py, and utils/fred_loader.py, each with the SAME ttl as
# the data it tracks. Streamlit freezes a cached return value at the moment
# it was computed, so calling this on every rerun returns the *actual* last-
# fetch time for that tier - not the current page-render time - until the
# ttl expires or the cache is cleared.


@st.cache_data(ttl=3600)
def _marker_1h():
    return datetime.now()


@st.cache_data(ttl=6 * 3600)
def _marker_6h():
    return datetime.now()


@st.cache_data(ttl=300)
def _marker_5m():
    return datetime.now()


def get_freshness() -> list:
    """One row per cache tier: label, human TTL, and the real timestamp that
    tier's data was last actually fetched from the internet."""
    return [
        {"label": "Prices & sectors", "ttl": "1 hour", "fetched_at": _marker_1h()},
        {"label": "Institutional positioning (COT) & liquidity (FRED)", "ttl": "6 hours", "fetched_at": _marker_6h()},
        {"label": "Crypto dominance", "ttl": "5 minutes", "fetched_at": _marker_5m()},
    ]


def format_age(fetched_at: datetime) -> str:
    """'3 min ago' / '2h 14m ago' - how long ago a tier was actually fetched."""
    seconds = max(0, (datetime.now() - fetched_at).total_seconds())
    if seconds < 60:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} min ago"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m ago"
