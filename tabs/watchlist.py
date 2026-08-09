import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import parse_tickers, load_price_data, get_ticker_names
from utils.indicators import display_dollar_volume, chaikin_money_flow, compute_rsi
from utils.scoring import score_ticker
from utils.theming import verdict_badge_html

RATIO_PAIRS = {
    "BTC / S&P 500": ("BTC-USD", "^GSPC"),
    "Gold / S&P 500": ("GLD", "^GSPC"),
    "Nasdaq / Dow": ("^IXIC", "^DJI"),
    "XLE / SPY (Energy vs Market)": ("XLE", "SPY"),
    "ETH / BTC": ("ETH-USD", "BTC-USD"),
}

_VERDICT_COLOR = {"Inflow": "#0ca30c", "Outflow": "#d03b3b", "Neutral": "#898781", "Unavailable": "#898781"}


def _is_index_ticker(ticker: str) -> bool:
    """Index tickers (^GSPC, ^IXIC, ...) aren't directly traded - Yahoo's
    "Volume" for them is a composite figure, not real dollar flow."""
    return ticker.startswith("^")


def _get_price_series(price_history, ticker: str):
    if price_history is None or price_history.empty:
        return None
    if isinstance(price_history.columns, pd.MultiIndex):
        try:
            return price_history["Close", ticker].dropna()
        except KeyError:
            return None
    if "Close" in price_history.columns:
        return price_history["Close"].dropna()
    return None


def _get_ohlcv(price_history, ticker: str):
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


def _build_signal_table(tickers, price_history, names):
    """One row per ticker: price/volume context plus the same composite
    money-flow verdict used on Overview/Evidence (utils.scoring.score_ticker) -
    real signal confluence (CMF + dollar-flow direction + MFI, CFTC
    positioning where available), not a single indicator's sign."""
    rows = []
    for t in tickers:
        frame = _get_ohlcv(price_history, t)
        entry = score_ticker(t, frame)
        if entry is None:
            continue

        close, volume = frame["Close"], frame["Volume"]
        day_chg = (close.iloc[-1] / close.iloc[-2] - 1) * 100 if len(close) >= 2 else np.nan
        vol_avg20 = volume.tail(20).mean()
        rel_vol = (volume.iloc[-1] / vol_avg20 * 100) if vol_avg20 and vol_avg20 > 0 else np.nan
        rsi = compute_rsi(close).iloc[-1]
        dv = np.nan if _is_index_ticker(t) else display_dollar_volume(t, close, volume).iloc[-1]

        rows.append({
            "Ticker": t,
            "Name": names.get(t, t),
            "Last Price": close.iloc[-1],
            "Day %": day_chg,
            "$ Volume": "—" if pd.isna(dv) else f"${dv:,.0f}",
            "Rel. Volume": "—" if pd.isna(rel_vol) else f"{rel_vol:.0f}%",
            "RSI (14)": rsi,
            "Verdict": entry["verdict"],
            "Score": entry["score"],
            "Reason": entry["reason"],
        })

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.reindex(df["Score"].abs().sort_values(ascending=False).index)


def _color_verdict(v):
    return f"color:{_VERDICT_COLOR.get(v, '#898781')}; font-weight:700"


def _color_signed(v):
    if pd.isna(v):
        return ""
    return "color:#0ca30c" if v > 0 else ("color:#d03b3b" if v < 0 else "")


def render():
    st.subheader("Watchlist")
    st.caption(
        "Type any tickers to get the same composite money-flow signal used on Overview/Evidence, applied to any asset — "
        "not just the curated 7. Ranked by conviction (largest |score| first)."
    )

    tickers_input = st.text_input(
        "Tickers (comma separated):",
        value="AAPL, MSFT, NVDA, TSLA, ^GSPC, GLD, BTC-USD",
        key="watchlist_tickers",
    )
    tickers = parse_tickers(tickers_input)
    if not tickers:
        st.error("Enter at least one valid ticker symbol.")
        return

    price_history = load_price_data(tickers=tickers, period="6mo", interval="1d")
    names = get_ticker_names(tuple(tickers))

    st.markdown("#### Signal Scanner")
    table = _build_signal_table(tickers, price_history, names)

    if table.empty:
        st.warning("Not enough daily price history for these tickers yet (need 21+ trading days).")
    else:
        styled = (
            table.style
            .map(_color_verdict, subset=["Verdict"])
            .map(_color_signed, subset=["Day %", "Score"])
            .format({
                "Last Price": "{:.2f}",
                "Day %": "{:+.2f}%",
                "RSI (14)": "{:.1f}",
                "Score": "{:+.2f}",
            })
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.caption(
            "Verdict blends Chaikin Money Flow, a 20-day dollar-flow ratio, and Money Flow Index (plus CFTC futures "
            "positioning for the 6 assets that have it — see Evidence). $ Volume shown as — for index tickers "
            "(^GSPC, ^IXIC, ...) since they aren't directly traded. Rel. Volume = today's volume ÷ its own 20-day average."
        )

    st.markdown("#### Inspect One Ticker")
    detail_ticker = st.selectbox("Ticker:", tickers, key="watchlist_detail_ticker")
    frame = _get_ohlcv(price_history, detail_ticker)
    entry = score_ticker(detail_ticker, frame)

    if entry is None:
        st.info("Not enough price history for this ticker.")
    else:
        badge_col, reason_col = st.columns([1, 3])
        with badge_col:
            st.markdown(verdict_badge_html(entry["verdict"]), unsafe_allow_html=True)
        with reason_col:
            st.write(entry["reason"])

        close, volume = frame["Close"], frame["Volume"]
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=close.index, y=close, name="Close", line=dict(width=2, color="#2a78d6")))
        fig_price.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Price", hovermode="x unified")
        st.plotly_chart(fig_price, use_container_width=True, key="watchlist_detail_price")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Chaikin Money Flow (20)**")
            cmf_series = chaikin_money_flow(frame["High"], frame["Low"], close, volume)
            fig_cmf = go.Figure()
            fig_cmf.add_trace(go.Scatter(x=cmf_series.index, y=cmf_series, line=dict(width=2, color="#1baf7a")))
            fig_cmf.add_hline(y=0, line_color="rgba(128,128,128,0.4)")
            fig_cmf.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified")
            st.plotly_chart(fig_cmf, use_container_width=True, key="watchlist_detail_cmf")
        with c2:
            st.markdown("**RSI (14)**")
            rsi_series = compute_rsi(close, window=14)
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=rsi_series.index, y=rsi_series, line=dict(width=2, color="#eda100")))
            fig_rsi.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, line_width=0)
            fig_rsi.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=0), yaxis_range=[0, 100], hovermode="x unified")
            st.plotly_chart(fig_rsi, use_container_width=True, key="watchlist_detail_rsi")

    with st.expander("Ratio Charts (optional)"):
        ratio_label = st.selectbox("Ratio:", list(RATIO_PAIRS.keys()), key="watchlist_ratio")
        base, quote = RATIO_PAIRS[ratio_label]
        base_series = _get_price_series(price_history, base)
        quote_series = _get_price_series(price_history, quote)
        if base_series is None or quote_series is None:
            st.info(f"Add {base} and {quote} to the ticker list above to see this ratio.")
        else:
            df = pd.concat([base_series, quote_series], axis=1, join="inner")
            df.columns = ["base", "quote"]
            ratio = (df["base"] / df["quote"]).dropna()
            fig_ratio = go.Figure()
            fig_ratio.add_trace(go.Scatter(x=ratio.index, y=ratio, mode="lines", name=f"{base}/{quote}"))
            fig_ratio.update_layout(height=280, hovermode="x unified")
            st.plotly_chart(fig_ratio, use_container_width=True, key="watchlist_ratio_chart")
