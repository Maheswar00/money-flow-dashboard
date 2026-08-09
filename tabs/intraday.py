import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from utils.indicators import volume_price_signal, dollar_volume


def _is_index_ticker(ticker: str) -> bool:
    """Index tickers (^GSPC, ^IXIC, ...) aren't directly traded - Yahoo's "Volume"
    for them is a composite figure, not shares actually changing hands, so price x
    volume doesn't produce a real dollar-flow number for these."""
    return ticker.startswith("^")


def _build_volume_scanner_table(tickers, avg_vol, intraday_df):
    rows = []

    if intraday_df is None or intraday_df.empty:
        return pd.DataFrame()

    if isinstance(intraday_df.columns, pd.MultiIndex):
        for t in tickers:
            try:
                vol = intraday_df["Volume", t].dropna()
                price = intraday_df["Close", t].dropna()
            except KeyError:
                continue

            if vol.empty or price.empty:
                continue

            cum_vol = vol.iloc[-1]
            last_price = price.iloc[-1]
            avg = avg_vol.get(t, np.nan)

            pct = (cum_vol / avg * 100) if avg and avg > 0 else np.nan
            # $ Volume lets you compare magnitude *across* tickers fairly (share
            # counts alone don't - a "share" of BTC-USD and a share of GLD aren't
            # the same unit of capital). % of Avg Volume is still the ranking basis
            # since it's already self-normalized per ticker. Skip $ figures for
            # index tickers - see _is_index_ticker().
            is_index = _is_index_ticker(t)
            dollar_vol = np.nan if is_index else dollar_volume(price, vol).iloc[-1]
            avg_dollar_vol = np.nan if is_index or not avg or avg <= 0 else avg * last_price

            rows.append({
                "Ticker": t,
                "Last Price": last_price,
                "$ Volume": dollar_vol,
                "~Avg Daily $ Volume": avg_dollar_vol,
                "% of Avg Volume": pct,
                "Signal": volume_price_signal(price, vol, window=20),
            })
    else:
        # Single-ticker case
        t = tickers[0]
        vol = intraday_df["Volume"].dropna()
        price = intraday_df["Close"].dropna()
        if not vol.empty and not price.empty:
            cum_vol = vol.iloc[-1]
            last_price = price.iloc[-1]
            avg = avg_vol.iloc[0]
            pct = (cum_vol / avg * 100) if avg > 0 else np.nan
            is_index = _is_index_ticker(t)
            dollar_vol = np.nan if is_index else dollar_volume(price, vol).iloc[-1]
            avg_dollar_vol = np.nan if is_index or avg <= 0 else avg * last_price

            rows.append({
                "Ticker": t,
                "Last Price": last_price,
                "$ Volume": dollar_vol,
                "~Avg Daily $ Volume": avg_dollar_vol,
                "% of Avg Volume": pct,
                "Signal": volume_price_signal(price, vol, window=20),
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("% of Avg Volume", ascending=False)
    return df

def render(tickers, avg_vol, intraday_df, price_history, timeframe_label):
    st.subheader("📊 Intraday Unusual Volume Scanner")

    table = _build_volume_scanner_table(tickers, avg_vol, intraday_df)

    if table.empty:
        st.warning("No intraday data. Market might be closed or tickers invalid.")
    else:
        # Pre-format $ columns to strings (incl. the "—" for index tickers) instead
        # of relying on Styler - st.dataframe's Arrow-based renderer shows NaN as
        # the literal text "None" regardless of Styler's na_rep.
        display_table = table.copy()
        for col in ["$ Volume", "~Avg Daily $ Volume"]:
            display_table[col] = table[col].apply(lambda v: "—" if pd.isna(v) else f"${v:,.0f}")

        st.dataframe(
            display_table.style.format({
                "Last Price": "{:.2f}",
                "% of Avg Volume": "{:.1f}",
            }),
            use_container_width=True,
        )
        st.caption(
            "$ Volume = price x volume, the fair unit for comparing capital traded across tickers with very different prices/share counts. "
            "Shown as — for index tickers (^GSPC, ^IXIC, ...) - they aren't directly traded, so Yahoo's volume figure for them isn't a real dollar-flow number."
        )

    st.markdown("### 📈 Multi‑Ticker Intraday Price Comparison")

    compare_tickers = st.multiselect(
        "Select tickers to compare:",
        tickers,
        default=[tickers[0]],
        key="intraday_multiselect"
    )

    fig = go.Figure()

    if price_history is not None and not price_history.empty:
        for t in compare_tickers:
            if isinstance(price_history.columns, pd.MultiIndex):
                try:
                    tdf = price_history.xs(t, axis=1, level=1)[["Close"]].dropna()
                except KeyError:
                    continue
            else:
                tdf = price_history[["Close"]].dropna()

            if tdf.empty:
                continue

            fig.add_trace(go.Scatter(
                x=tdf.index,
                y=tdf["Close"],
                mode="lines",
                name=t,
                line=dict(width=2),
            ))

    fig.update_layout(
        height=450,
        title=f"Price Comparison ({timeframe_label})",
        xaxis_title="Time",
        yaxis_title="Price",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.2),
    )

    st.plotly_chart(fig, use_container_width=True, key="intraday_price_chart")

    st.markdown("### 🧪 Volume / Price Confirmation (Signals)")
    if not table.empty:
        st.dataframe(
            table[["Ticker", "% of Avg Volume", "Signal"]].style.format({
                "% of Avg Volume": "{:.1f}",
            }),
            use_container_width=True,
        )
    else:
        st.info("No volume/price signals available yet.")
