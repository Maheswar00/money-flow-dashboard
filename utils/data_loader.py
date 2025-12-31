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
    df = yf.download(list(assets.values()), period="1y", interval="1d")["Close"]
    df.columns = assets.keys()
    return assets, df
