import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import parse_tickers, load_intraday_volume_data, load_price_data
from utils.indicators import dollar_volume, chaikin_money_flow, compute_rsi
from utils.scoring import cmf_label

RATIO_PAIRS = {
    "BTC / S&P 500": ("BTC-USD", "^GSPC"),
    "Gold / S&P 500": ("GLD", "^GSPC"),
    "Nasdaq / Dow": ("^IXIC", "^DJI"),
    "XLE / SPY (Energy vs Market)": ("XLE", "SPY"),
    "ETH / BTC": ("ETH-USD", "BTC-USD"),
}

TIMEFRAMES = {
    "1 Day": ("1d", "5m"),
    "5 Days": ("5d", "15m"),
    "1 Month": ("1mo", "30m"),
    "3 Months": ("3mo", "1h"),
    "1 Year": ("1y", "1d"),
}


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


def _build_scanner_table(tickers, avg_vol, intraday_df):
    rows = []
    if intraday_df is None or intraday_df.empty:
        return pd.DataFrame()

    multi = isinstance(intraday_df.columns, pd.MultiIndex)
    ticker_list = tickers if multi else tickers[:1]

    for t in ticker_list:
        try:
            if multi:
                high, low = intraday_df["High", t].dropna(), intraday_df["Low", t].dropna()
                close, vol = intraday_df["Close", t].dropna(), intraday_df["Volume", t].dropna()
            else:
                high, low = intraday_df["High"].dropna(), intraday_df["Low"].dropna()
                close, vol = intraday_df["Close"].dropna(), intraday_df["Volume"].dropna()
        except KeyError:
            continue
        if close.empty or vol.empty:
            continue

        last_price = close.iloc[-1]
        cum_vol = vol.iloc[-1]
        avg = avg_vol.get(t, np.nan) if multi else avg_vol.iloc[0]
        pct = (cum_vol / avg * 100) if avg and avg > 0 else np.nan

        is_index = _is_index_ticker(t)
        dv = np.nan if is_index else dollar_volume(close, vol).iloc[-1]

        cmf = np.nan
        if len(close) >= 21:
            joined = pd.concat([high, low, close, vol], axis=1).dropna()
            joined.columns = ["High", "Low", "Close", "Volume"]
            if len(joined) >= 21:
                cmf = chaikin_money_flow(joined["High"], joined["Low"], joined["Close"], joined["Volume"]).iloc[-1]

        rows.append({
            "Ticker": t,
            "Last Price": last_price,
            "$ Volume": dv,
            "% of Avg Volume": pct,
            "Signal": cmf_label(cmf),
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("% of Avg Volume", ascending=False)


def render():
    st.subheader("Watchlist")
    st.caption("Type any tickers to scan for unusual volume, compare prices, and check RSI — a general-purpose tool, separate from the curated Overview scorecard.")

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        tickers_input = st.text_input(
            "Tickers (comma separated):",
            value="^GSPC, ^IXIC, GLD, USO, TLT, BTC-USD, ETH-USD",
            key="watchlist_tickers",
        )
    with c2:
        interval = st.selectbox("Intraday interval:", ["1m", "2m", "5m", "15m"], index=2, key="watchlist_interval")
    with c3:
        timeframe_label = st.selectbox("Chart timeframe:", list(TIMEFRAMES.keys()), index=0, key="watchlist_timeframe")

    tickers = parse_tickers(tickers_input)
    if not tickers:
        st.error("Enter at least one valid ticker symbol.")
        return

    period, chart_interval = TIMEFRAMES[timeframe_label]
    avg_vol, intraday_df = load_intraday_volume_data(tickers=tickers, history_days=20, interval=interval)
    price_history = load_price_data(tickers=tickers, period=period, interval=chart_interval)

    st.markdown("#### Unusual Volume Scanner")
    table = _build_scanner_table(tickers, avg_vol, intraday_df)
    if table.empty:
        st.warning("No intraday data. Market might be closed or tickers invalid.")
    else:
        st.dataframe(
            table.style.format({
                "Last Price": "{:.2f}",
                "% of Avg Volume": "{:.1f}",
                "$ Volume": lambda v: "—" if pd.isna(v) else f"${v:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("$ Volume shown as — for index tickers (^GSPC, ^IXIC, ...) — they aren't directly traded, so Yahoo's volume figure for them isn't a real dollar-flow number.")

    st.markdown("#### Price Comparison")
    compare_tickers = st.multiselect("Select tickers:", tickers, default=[tickers[0]], key="watchlist_compare")
    normalize = st.checkbox("Normalize to % change", value=len(compare_tickers) > 1, key="watchlist_normalize")

    fig = go.Figure()
    for t in compare_tickers:
        series = _get_price_series(price_history, t)
        if series is None or series.empty:
            continue
        y = (series / series.iloc[0] - 1) * 100 if normalize else series
        fig.add_trace(go.Scatter(x=series.index, y=y, mode="lines", name=t, line=dict(width=2)))
    fig.update_layout(
        height=380, xaxis_title="Time", yaxis_title="% Change" if normalize else "Price",
        hovermode="x unified", legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig, use_container_width=True, key="watchlist_price_chart")

    col_rsi, col_ratio = st.columns(2)
    with col_rsi:
        st.markdown("#### RSI")
        rsi_ticker = st.selectbox("Ticker:", tickers, key="watchlist_rsi_ticker")
        series = _get_price_series(price_history, rsi_ticker)
        if series is None or series.empty:
            st.info("No price data for RSI.")
        else:
            rsi = compute_rsi(series, window=14)
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=rsi.index, y=rsi, mode="lines", name=f"RSI(14)"))
            fig_rsi.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, line_width=0)
            fig_rsi.update_layout(height=280, hovermode="x unified", yaxis_range=[0, 100])
            st.plotly_chart(fig_rsi, use_container_width=True, key="watchlist_rsi_chart")

    with col_ratio:
        st.markdown("#### Ratio Charts")
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
