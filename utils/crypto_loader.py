import requests
import streamlit as st

COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"


@st.cache_data(ttl=300)
def load_crypto_dominance() -> dict:
    """BTC/ETH dominance and total crypto market cap, from CoinGecko's public
    global endpoint (no API key required). Empty dict on failure - callers
    should treat that as "data unavailable"."""
    try:
        resp = requests.get(COINGECKO_GLOBAL_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()["data"]
    except Exception as e:
        print(f"⚠ Error fetching CoinGecko global data: {e}")
        return {}

    dominance = data.get("market_cap_percentage", {})
    return {
        "btc_dominance": dominance.get("btc"),
        "eth_dominance": dominance.get("eth"),
        "total_market_cap_usd": data.get("total_market_cap", {}).get("usd"),
        "market_cap_change_pct_24h": data.get("market_cap_change_percentage_24h_usd"),
    }
