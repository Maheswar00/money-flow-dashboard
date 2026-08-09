import streamlit as st
import pandas as pd

from utils.indicators import money_flow_index, chaikin_money_flow
from utils.cot_loader import latest_positioning_table


def _get_ohlcv(price_history: pd.DataFrame, ticker: str):
    if price_history is None or price_history.empty:
        return None

    if isinstance(price_history.columns, pd.MultiIndex):
        try:
            frame = pd.concat(
                [price_history["High", ticker], price_history["Low", ticker],
                 price_history["Close", ticker], price_history["Volume", ticker]],
                axis=1,
            )
        except KeyError:
            return None
    else:
        needed = {"High", "Low", "Close", "Volume"}
        if not needed.issubset(price_history.columns):
            return None
        frame = price_history[["High", "Low", "Close", "Volume"]]

    frame.columns = ["High", "Low", "Close", "Volume"]
    frame = frame.dropna()
    return frame if not frame.empty else None


def _interpret(mfi, cmf):
    parts = []
    if pd.notna(mfi):
        if mfi >= 80:
            parts.append("Overbought / distribution risk")
        elif mfi <= 20:
            parts.append("Oversold / accumulation zone")
    if pd.notna(cmf):
        if cmf > 0.05:
            parts.append("Buying pressure")
        elif cmf < -0.05:
            parts.append("Selling pressure")
    return "; ".join(parts) if parts else "Neutral"


def _cot_read(row):
    if pd.isna(row["WoW Change"]):
        return ""
    net, chg = row["Net Large-Spec Position"], row["WoW Change"]
    if net > 0 and chg > 0:
        return "Net long & increasing → adding risk"
    if net > 0 and chg < 0:
        return "Net long & trimming"
    if net < 0 and chg < 0:
        return "Net short & increasing → adding hedges/bearish bets"
    if net < 0 and chg > 0:
        return "Net short & covering"
    return ""


def render(tickers, price_history: pd.DataFrame, intraday_df: pd.DataFrame, macro_prices: pd.DataFrame, cot_df: pd.DataFrame = None):
    st.subheader("🧭 Smart Money Signals")

    st.markdown("### 1️⃣ Money Flow Index & Chaikin Money Flow by Ticker")
    st.caption("Volume-weighted indicators - whether volume is actually confirming the price move, not just price direction alone.")

    rows = []
    for t in tickers:
        ohlcv = _get_ohlcv(price_history, t)
        if ohlcv is None or len(ohlcv) < 20:
            continue

        mfi = money_flow_index(ohlcv["High"], ohlcv["Low"], ohlcv["Close"], ohlcv["Volume"]).iloc[-1]
        cmf = chaikin_money_flow(ohlcv["High"], ohlcv["Low"], ohlcv["Close"], ohlcv["Volume"]).iloc[-1]

        rows.append({
            "Ticker": t,
            "MFI (14)": mfi,
            "CMF (20)": cmf,
            "Read": _interpret(mfi, cmf),
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.format({"MFI (14)": "{:.1f}", "CMF (20)": "{:.3f}"}),
            use_container_width=True,
        )
    else:
        st.info("Not enough price history to compute MFI/CMF yet — try a longer timeframe.")

    st.markdown("### 2️⃣ Institutional Positioning (CFTC Commitment of Traders)")
    st.caption("Net large-speculator futures positioning — the closest free proxy to 'what is big money actually doing'.")

    table = latest_positioning_table(cot_df) if cot_df is not None else pd.DataFrame()
    if table.empty:
        st.info("COT data unavailable right now.")
    else:
        table = table.copy()
        table["Read"] = table.apply(_cot_read, axis=1)
        st.dataframe(
            table.style.format({
                "Net Large-Spec Position": "{:,.0f}",
                "% of Open Interest": "{:.1f}%",
                "WoW Change": "{:+,.0f}",
            }),
            use_container_width=True,
        )
        st.caption("Source: CFTC Commitments of Traders (Legacy Futures-Only), published weekly (Fridays, as-of Tuesday's data).")

    st.markdown("### 3️⃣ Macro Regime (Very Rough Heuristic)")

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
