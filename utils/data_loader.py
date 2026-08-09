import streamlit as st
import yfinance as yf
import pandas as pd

def parse_tickers(raw: str) -> list:
    parts = [p.strip().upper() for p in raw.split(",") if p.strip()]
    # Filter out label-like entries starting/ending with '='
    return [p for p in parts if not p.startswith("=") and not p.endswith("=")]

@st.cache_data(ttl=120)
def get_avg_volume(tickers, days):
    data = yf.download(
        tickers=tickers,
        period=f"{days}d",
        interval="1d",
        progress=False,
    )
    if isinstance(data.columns, pd.MultiIndex):
        vol = data["Volume"]
    else:
        vol = data["Volume"].to_frame()
    return vol.mean()

@st.cache_data(ttl=30)
def get_intraday(tickers, interval):
    return yf.download(
        tickers=tickers,
        period="1d",
        interval=interval,
        progress=False,
    )

@st.cache_data(ttl=60)
def load_price_data(tickers, period, interval):
    return yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        progress=False,
    )

def load_intraday_volume_data(tickers, history_days, interval):
    avg_vol = get_avg_volume(tickers, history_days)
    intraday_df = get_intraday(tickers, interval)
    return avg_vol, intraday_df

def load_price_history(tickers, period, interval):
    return load_price_data(tickers, period, interval)


def _extract_close_column(df, ticker):
    """Pull a single ticker's Close series out of a (possibly batched) download."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        if "Close" not in df.columns.get_level_values(0):
            return None
        close = df["Close"]
        if ticker in close.columns:
            return close[ticker]
        # Single-ticker batch call still yields one column - take it.
        return close.iloc[:, 0] if close.shape[1] == 1 else None

    if "Close" in df.columns:
        return df["Close"]

    return None


def _load_universe(assets: dict, fallback: dict = None, period: str = "1y") -> pd.DataFrame:
    """Batch-download Close prices for a labeled set of tickers, with an optional
    batched fallback pass for whichever ones fail. Shared by load_macro_universe()
    and load_sector_universe() - one or two network round-trips total, never one
    request per asset."""
    fallback = fallback or {}
    clean = {}

    primary_tickers = list(assets.values())
    try:
        primary_df = yf.download(primary_tickers, period=period, interval="1d", progress=False)
    except Exception as e:
        print(f"⚠ Error batch-fetching primary tickers: {e}")
        primary_df = pd.DataFrame()

    missing = {}
    for label, ticker in assets.items():
        series = _extract_close_column(primary_df, ticker)
        s = series.dropna() if isinstance(series, pd.Series) else None
        if s is not None and not s.empty:
            clean[label] = s
        else:
            missing[label] = ticker

    fallback_needed = {
        label: fallback[label] for label in missing if label in fallback
    }
    if fallback_needed:
        fallback_tickers = list(fallback_needed.values())
        try:
            fallback_df = yf.download(fallback_tickers, period=period, interval="1d", progress=False)
        except Exception as e:
            print(f"⚠ Error batch-fetching fallback tickers: {e}")
            fallback_df = pd.DataFrame()

        for label, alt in fallback_needed.items():
            series = _extract_close_column(fallback_df, alt)
            s = series.dropna() if isinstance(series, pd.Series) else None
            if s is not None and not s.empty:
                clean[label] = s
                print(f"✅ Using fallback for {label}: {alt}")
            else:
                print(f"❌ No valid data for {label} (primary {assets[label]}, fallback {alt})")

    for label in missing:
        if label not in fallback:
            print(f"❌ No valid data for {label} ({assets[label]}), no fallback configured")

    if not clean:
        return pd.DataFrame()

    prices = pd.DataFrame(clean).dropna(how="all")
    # Crypto trades 24/7; equities/commodities/bonds/FX don't. On a weekend or
    # holiday, that leaves the most recent row(s) NaN for every non-crypto column,
    # which silently breaks every .iloc[-1]-based return/momentum calculation
    # downstream (heatmaps, momentum ranking, etc). Forward-fill carries the last
    # real close forward, same as a human reading "current price" over a weekend.
    return prices.ffill()


@st.cache_data(ttl=3600)
def load_macro_universe():
    assets = {
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "Gold": "GLD",
        "Oil": "USO",
        "Bonds (20Y)": "TLT",
        "US Dollar Index": "DX-Y.NYB",
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD",
    }

    fallback = {
        "S&P 500": "SPY",
        "Nasdaq": "QQQ",
        "Gold": "IAU",
        "Oil": "CL=F",
        "Bonds (20Y)": "IEF",
        "US Dollar Index": "UUP",
    }

    prices = _load_universe(assets, fallback)
    return assets, prices


# Tradable ETF/spot proxies for each broad asset class - deliberately NOT the
# index tickers (^GSPC, ^IXIC): those aren't directly traded, so Yahoo's Volume
# figure for them can't be turned into a real dollar-flow number (see
# tabs/intraday.py's _is_index_ticker for the same issue elsewhere).
FLOW_PROXIES = {
    "US Equities (SPY)": "SPY",
    "Nasdaq Equities (QQQ)": "QQQ",
    "Gold (GLD)": "GLD",
    "Oil (USO)": "USO",
    "Bonds (TLT)": "TLT",
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
}


@st.cache_data(ttl=3600)
def load_flow_universe(period: str = "6mo"):
    """High/Low/Close/Volume (full OHLCV, not just Close) for the FLOW_PROXIES
    tickers, one batched download - needed for CMF/MFI and the dollar-volume
    flow proxy used by utils/scoring.py."""
    tickers = list(FLOW_PROXIES.values())
    try:
        df = yf.download(tickers, period=period, interval="1d", progress=False)
    except Exception as e:
        print(f"⚠ Error batch-fetching flow-proxy tickers: {e}")
        return {}

    out = {}
    for label, ticker in FLOW_PROXIES.items():
        try:
            if isinstance(df.columns, pd.MultiIndex):
                high, low = df["High"][ticker], df["Low"][ticker]
                close, volume = df["Close"][ticker], df["Volume"][ticker]
            else:
                high, low = df["High"], df["Low"]
                close, volume = df["Close"], df["Volume"]
        except KeyError:
            continue

        frame = pd.concat([high, low, close, volume], axis=1)
        frame.columns = ["High", "Low", "Close", "Volume"]
        frame = frame.dropna()
        if not frame.empty:
            out[label] = frame
        else:
            print(f"❌ No valid OHLCV data for {label} ({ticker})")

    return out


@st.cache_data(ttl=3600)
def load_sector_universe():
    """S&P 500 sector SPDR ETFs, for tracking rotation *within* equities
    (playbook point #5), not just across broad asset classes."""
    assets = {
        "Technology": "XLK",
        "Financials": "XLF",
        "Energy": "XLE",
        "Health Care": "XLV",
        "Consumer Discretionary": "XLY",
        "Consumer Staples": "XLP",
        "Industrials": "XLI",
        "Materials": "XLB",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Communication Services": "XLC",
    }

    prices = _load_universe(assets)
    return assets, prices
