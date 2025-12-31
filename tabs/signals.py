import streamlit as st
import pandas as pd

from utils.indicators import volume_price_signal

def render(tickers, price_history: pd.DataFrame, intraday_df: pd.DataFrame, macro_prices: pd.DataFrame):
    st.subheader("🧭 Smart Money Signals")

    st.markdown("### 1️⃣ Volume / Price Confirmation by Ticker")

    rows = []

    if intraday_df is not None and not intraday_df.empty:
        if isinstance(intraday_df.columns, pd.MultiIndex):
            for t in tickers:
                try:
                    vol = intraday_df["Volume", t].dropna()
                    price = intraday_df["Close", t].dropna()
                except KeyError:
                    continue
                if vol.empty or price.empty:
                    continue
                sig = volume_price_signal(price, vol, window=20)
                rows.append({"Ticker": t, "Signal": sig})
        else:
            t = tickers[0]
            vol = intraday_df["Volume"].dropna()
            price = intraday_df["Close"].dropna()
            if not vol.empty and not price.empty:
                sig = volume_price_signal(price, vol, window=20)
                rows.append({"Ticker": t, "Signal": sig})

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No intraday data to compute signals.")

    st.markdown("### 2️⃣ Macro Regime (Very Rough Heuristic)")

    if macro_prices is None or macro_prices.empty:
        st.info("No macro data available for regime detection.")
        return

    last = macro_prices.iloc[-1]
    first = macro_prices.iloc[0]
    perf = (last / first - 1) * 100

    regime_notes = []

    if "S&P 500" in perf and "Bitcoin" in perf:
        if perf["S&P 500"] > 0 and perf["Bitcoin"] > 0:
            regime_notes.append("Risk assets (Stocks + Crypto) positive → Risk‑on bias.")
        if perf["S&P 500"] < 0 and perf["Bitcoin"] < 0:
            regime_notes.append("Stocks & Crypto both weak → Risk‑off / defensive regime.")

    if "Gold" in perf and perf["Gold"] > 0:
        regime_notes.append("Gold positive over the period → demand for safety / inflation hedge.")

    if "Bonds (20Y)" in perf and perf["Bonds (20Y)"] > 0:
        regime_notes.append("Long‑duration bonds positive → falling yields / duration bid.")

    if not regime_notes:
        st.write("No strong macro regime signal from this simple heuristic.")
    else:
        for note in regime_notes:
            st.write(f"- {note}")

    st.markdown("""
These are **first‑pass, rough signals**.  
You can refine them with:
- Yield curve data
- Credit spreads
- Volatility indices (VIX, MOVE)
- Liquidity metrics (Fed balance sheet, M2, etc.)
""")
