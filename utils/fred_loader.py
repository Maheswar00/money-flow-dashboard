import pandas as pd
import streamlit as st

# FRED's public CSV export - no API key required.
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

FRED_SERIES = {
    "Fed Balance Sheet ($B)": "WALCL",
    "ON Reverse Repo ($B)": "RRPONTSYD",
    "M2 Money Supply ($B)": "M2SL",
    "10Y Treasury Yield (%)": "DGS10",
}

# WALCL is published by FRED in millions of dollars; RRPONTSYD and M2SL are
# already in billions. Normalize WALCL so all three "$B" series are comparable.
_SCALE_TO_BILLIONS = {"WALCL": 1 / 1000}


@st.cache_data(ttl=6 * 3600)
def load_fred_series(lookback_days: int = 3 * 365) -> pd.DataFrame:
    """Macro liquidity conditions: Fed balance sheet, reverse repo, M2, 10Y yield.
    Series have different native frequencies (daily/weekly/monthly) - forward-filled
    onto a common daily index so they can be plotted together. Trimmed to a recent
    window (default 3y) - these series have very different start dates (DGS10 back
    to 1962, WALCL only from ~2002), so an "indexed to 100 at the first row" chart
    over full history would divide by NaN for the shorter series.
    Empty DataFrame on failure - callers should treat that as "data unavailable"."""
    series = {}
    for label, series_id in FRED_SERIES.items():
        try:
            df = pd.read_csv(FRED_CSV_URL.format(series_id=series_id))
            df.columns = ["Date", "Value"]
            df["Date"] = pd.to_datetime(df["Date"])
            df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
            scale = _SCALE_TO_BILLIONS.get(series_id, 1)
            s = df.dropna().set_index("Date")["Value"] * scale
            if not s.empty:
                series[label] = s
            else:
                print(f"⚠ FRED series {label} ({series_id}) returned no usable rows")
        except Exception as e:
            print(f"⚠ Error fetching FRED series {label} ({series_id}): {e}")

    if not series:
        return pd.DataFrame()

    combined = pd.DataFrame(series).sort_index()
    combined = combined.ffill()
    cutoff = combined.index.max() - pd.Timedelta(days=lookback_days)
    combined = combined[combined.index >= cutoff]
    return combined
