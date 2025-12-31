import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils.indicators import compute_rsi

RATIO_PAIRS = {
    "BTC / S&P 500": ("BTC-USD", "^GSPC"),
    "Gold / S&P 500": ("GLD", "^GSPC"),
    "Nasdaq / Dow": ("^IXIC", "^DJI"),
    "XLE / SPY (Energy vs Market)": ("XLE", "SPY"),
    "ETH / BTC": ("ETH-USD", "BTC-USD"),
}

def _get_price_series(price_history, ticker: str) -> pd.Series | None:
    if price_history is None or price_history.empty:
        return None
    if isinstance(price_history.columns, pd.MultiIndex):
        try:
            return price_history["Close", ticker].dropna()
        except KeyError:
            return None
    else:
        if "Close" in price_history.columns:
            return price_history["Close"].dropna()
        return None

def render(tickers, price_history, timeframe_label):
    st.subheader("📈 Multi‑Ticker Price Comparison & Technicals")

    normalize = st.checkbox("Normalize to % change (start = 0%)", value=False)

    compare_tickers = st.multiselect(
        "Select tickers to compare:",
        tickers,
        default=[tickers[0]],
        key="comparison_multiselect"
    )

    fig = go.Figure()

    for t in compare_tickers:
        series = _get_price_series(price_history, t)
        if series is None or series.empty:
            continue

        y = (series / series.iloc[0] - 1) * 100 if normalize else series

        fig.add_trace(go.Scatter(
            x=series.index,
            y=y,
            mode="lines",
            name=t,
            line=dict(width=2),
        ))

    fig.update_layout(
        height=450,
        title=f"Price Comparison ({timeframe_label})",
        xaxis_title="Time",
        yaxis_title="% Change" if normalize else "Price",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.2),
    )

    st.plotly_chart(fig, use_container_width=True, key="comparison_price_chart")

    st.markdown("### 📉 RSI (Relative Strength Index)")

    rsi_ticker = st.selectbox("Select ticker for RSI:", tickers)
    series = _get_price_series(price_history, rsi_ticker)

    if series is None or series.empty:
        st.info("No price data for RSI.")
    else:
        rsi = compute_rsi(series, window=14)

        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(
            x=rsi.index,
            y=rsi,
            mode="lines",
            name=f"RSI(14) – {rsi_ticker}",
        ))
        fig_rsi.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, line_width=0)
        fig_rsi.update_layout(
            height=250,
            xaxis_title="Time",
            yaxis_title="RSI",
            hovermode="x unified",
        )
        st.plotly_chart(fig_rsi, use_container_width=True, key="comparison_rsi_chart")

    st.markdown("### ⚖ Ratio Charts (Capital Preference)")

    ratio_label = st.selectbox("Select ratio:", list(RATIO_PAIRS.keys()))
    base, quote = RATIO_PAIRS[ratio_label]

    base_series = _get_price_series(price_history, base)
    quote_series = _get_price_series(price_history, quote)

    if base_series is None or quote_series is None:
        st.info("Not enough data for this ratio in the current timeframe.")
        return

    df = pd.concat([base_series, quote_series], axis=1, join="inner")
    df.columns = ["base", "quote"]
    ratio = (df["base"] / df["quote"]).dropna()

    fig_ratio = go.Figure()
    fig_ratio.add_trace(go.Scatter(
        x=ratio.index,
        y=ratio,
        mode="lines",
        name=f"{base} / {quote}",
    ))
    fig_ratio.update_layout(
        height=300,
        xaxis_title="Time",
        yaxis_title="Ratio",
        hovermode="x unified",
    )
    st.plotly_chart(fig_ratio, use_container_width=True, key="comparison_ratio_chart")
