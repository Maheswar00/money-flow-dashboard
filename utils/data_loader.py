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

print("SPY test:", yf.download("SPY", period="1y", interval="1d").head())


@st.cache_data(ttl=3600)
def load_macro_universe():
    import pandas as pd
    import yfinance as yf

    # -----------------------------
    # Helper: extract Close prices
    # -----------------------------
    def extract_close(df):
        if not isinstance(df, pd.DataFrame) or df.empty:
            return None

        # MultiIndex columns (your current case)
        if isinstance(df.columns, pd.MultiIndex):
            if "Close" in df.columns.get_level_values(0):
                return df["Close"].iloc[:, 0]

        # Old single-index format
        if "Close" in df.columns:
            return df["Close"]

        return None

    # -----------------------------
    # Asset universe
    # -----------------------------
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

    clean = {}

    # -----------------------------
    # Download + clean loop
    # -----------------------------
    for label, ticker in assets.items():
        series = None

        # Primary ticker
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            close = extract_close(df)

            if isinstance(close, pd.Series):
                s = close.dropna()
                if not s.empty:
                    series = s
                else:
                    print(f"⚠ Empty Close data for {label} ({ticker})")
            else:
                print(f"⚠ No Close price found for {label} ({ticker})")

        except Exception as e:
            print(f"⚠ Error fetching {label} ({ticker}): {e}")

        # Fallback ticker
        if series is None and label in fallback:
            alt = fallback[label]
            try:
                df_alt = yf.download(alt, period="1y", interval="1d", progress=False)
                close_alt = extract_close(df_alt)

                if isinstance(close_alt, pd.Series):
                    s_alt = close_alt.dropna()
                    if not s_alt.empty:
                        series = s_alt
                        print(f"✅ Using fallback for {label}: {alt}")
                    else:
                        print(f"⚠ Fallback Close empty for {label} ({alt})")
                else:
                    print(f"⚠ Fallback missing Close for {label} ({alt})")

            except Exception as e:
                print(f"⚠ Error fetching fallback {label} ({alt}): {e}")

        # Store valid series
        if isinstance(series, pd.Series) and not series.empty:
            clean[label] = series
        else:
            print(f"❌ No valid data for {label}")

    # -----------------------------
    # Final assembly
    # -----------------------------
    print("DEBUG clean keys:", list(clean.keys()))

    if not clean:
        return assets, pd.DataFrame()

    prices = pd.DataFrame(clean).dropna(how="all")

    return assets, prices
