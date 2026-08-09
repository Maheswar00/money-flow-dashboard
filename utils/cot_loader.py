import datetime as dt

import pandas as pd
import requests
import streamlit as st

# CFTC "Commitments of Traders" (legacy, futures-only) Socrata dataset.
# Free, public, no API key required.
COT_API_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

# Friendly label -> exact CFTC market_and_exchange_names value.
# Verified live against the CFTC API to have data reported within the last 3 months -
# several "obvious" contract names (old Nasdaq/WTI labels, ICE Dollar Index) turned out
# to be discontinued or renamed, some as far back as 1999, and were swapped for the
# names CFTC currently reports under. ICE's US Dollar Index COT report has had no new
# data since 2022-02-01 in either the Legacy or Traders-in-Financial-Futures datasets,
# so it's excluded here rather than shown stale.
COT_MARKETS = {
    "S&P 500 (Equities)": "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
    "Nasdaq 100 (Equities)": "NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE",
    "10Y Treasury (Bonds)": "UST 10Y NOTE - CHICAGO BOARD OF TRADE",
    "Gold": "GOLD - COMMODITY EXCHANGE INC.",
    "Crude Oil (WTI)": "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
    "Bitcoin": "BITCOIN - CHICAGO MERCANTILE EXCHANGE",
}


@st.cache_data(ttl=6 * 3600)
def load_cot_positioning(lookback_weeks: int = 26) -> pd.DataFrame:
    """Large-speculator ("smart money") net futures positioning per tracked market.

    Returns a tidy DataFrame with one row per market per report date:
    Label, Date, NetPosition, PctOI, OpenInterest. Empty DataFrame on failure -
    callers should treat that as "data unavailable" rather than crash.
    """
    market_names = list(COT_MARKETS.values())
    cutoff = (dt.date.today() - dt.timedelta(weeks=lookback_weeks)).isoformat()

    quoted_names = ",".join(f"'{name}'" for name in market_names)
    where_clause = (
        f"market_and_exchange_names in({quoted_names}) "
        f"AND report_date_as_yyyy_mm_dd > '{cutoff}'"
    )

    params = {
        "$select": (
            "market_and_exchange_names,report_date_as_yyyy_mm_dd,"
            "noncomm_positions_long_all,noncomm_positions_short_all,open_interest_all"
        ),
        "$where": where_clause,
        "$order": "report_date_as_yyyy_mm_dd ASC",
        "$limit": 5000,
    }

    try:
        resp = requests.get(COT_API_URL, params=params, timeout=20)
        resp.raise_for_status()
        rows = resp.json()
    except Exception as e:
        print(f"⚠ Error fetching CFTC COT data: {e}")
        return pd.DataFrame()

    if not rows:
        print("⚠ CFTC COT query returned no rows")
        return pd.DataFrame()

    name_to_label = {v: k for k, v in COT_MARKETS.items()}
    df = pd.DataFrame(rows)
    df["Label"] = df["market_and_exchange_names"].map(name_to_label)
    df["Date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
    df["OpenInterest"] = pd.to_numeric(df["open_interest_all"], errors="coerce")
    df["NetPosition"] = pd.to_numeric(df["noncomm_positions_long_all"], errors="coerce") - pd.to_numeric(
        df["noncomm_positions_short_all"], errors="coerce"
    )
    df["PctOI"] = (df["NetPosition"] / df["OpenInterest"].replace(0, pd.NA)) * 100

    return df[["Label", "Date", "NetPosition", "PctOI", "OpenInterest"]].dropna(subset=["Label"]).sort_values(
        ["Label", "Date"]
    )


def latest_positioning_table(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse the tidy history into one row per market: latest reading + WoW change."""
    if df is None or df.empty:
        return pd.DataFrame()

    rows = []
    for label, g in df.groupby("Label"):
        g = g.sort_values("Date")
        if g.empty:
            continue
        latest = g.iloc[-1]
        prior = g.iloc[-2] if len(g) > 1 else None
        wow_change = latest["NetPosition"] - prior["NetPosition"] if prior is not None else None
        rows.append(
            {
                "Market": label,
                "Report Date": latest["Date"].date(),
                "Net Large-Spec Position": latest["NetPosition"],
                "% of Open Interest": latest["PctOI"],
                "WoW Change": wow_change,
            }
        )
    return pd.DataFrame(rows)
