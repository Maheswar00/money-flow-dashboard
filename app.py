import streamlit as st
from datetime import datetime

from utils.data_loader import (
    parse_tickers,
    load_intraday_volume_data,
    load_price_history,
    load_macro_universe,
)
from utils.theming import set_page_config_and_theme

from tabs import intraday, comparison, macro, heatmaps, flows, signals, playbook

# ---------------------------------------------------------
# PAGE CONFIG / THEME
# ---------------------------------------------------------
set_page_config_and_theme()

st.title("💸 Money Flow Dashboard (Stocks + Crypto + Macro)")

# ---------------------------------------------------------
# SIDEBAR – GLOBAL CONTROLS
# ---------------------------------------------------------
st.sidebar.header("Global Settings")

tickers_input = st.sidebar.text_input(
    "Tickers (comma separated):",
    value=(
        "=== STOCK INDEXES ===, "
        "^GSPC, ^IXIC, "
        "=== COMMODITIES ===, "
        "GLD, USO, "
        "=== BONDS ===, "
        "TLT, "
        "=== CURRENCY ===, "
        "DX-Y.NYB, "
        "=== CRYPTO ===, "
        "BTC-USD, ETH-USD"
    )
)

intraday_interval = st.sidebar.selectbox(
    "Intraday interval (volume scanner):",
    ["1m", "2m", "5m", "15m"],
    index=2,
)

history_days = st.sidebar.slider(
    "Days for average volume:",
    5, 60, 20,
)

TIMEFRAMES = {
    "1 Day": ("1d", "5m"),
    "5 Days": ("5d", "15m"),
    "1 Month": ("1mo", "30m"),
    "3 Months": ("3mo", "1h"),
    "6 Months": ("6mo", "2h"),
    "1 Year": ("1y", "1d"),
    "YTD": ("ytd", "1d"),
    "Max": ("max", "1d"),
}

timeframe_label = st.sidebar.selectbox(
    "Chart timeframe:",
    list(TIMEFRAMES.keys()),
    index=0,
)
period, chart_interval = TIMEFRAMES[timeframe_label]

momentum_window = st.sidebar.slider(
    "Momentum window (days):",
    min_value=3,
    max_value=90,
    value=20,
    step=1,
)

auto_refresh = st.sidebar.checkbox("Enable auto-refresh", value=False)
if auto_refresh:
    st.experimental_set_query_params(ts=str(datetime.now().timestamp()))

tickers = parse_tickers(tickers_input)
if not tickers:
    st.error("Enter at least one valid ticker symbol.")
    st.stop()

# ---------------------------------------------------------
# GLOBAL DATA LOADS (SHARED ACROSS TABS)
# ---------------------------------------------------------
avg_vol, intraday_df = load_intraday_volume_data(
    tickers=tickers,
    history_days=history_days,
    interval=intraday_interval,
)

price_history = load_price_history(
    tickers=tickers,
    period=period,
    interval=chart_interval,
)

macro_assets, macro_prices = load_macro_universe()

# ---------------------------------------------------------
# TABS
# ---------------------------------------------------------
tab_labels = [
    "📊 Intraday Scanner",
    "📈 Comparison & Technicals",
    "🌍 Macro Capital Flow",
    "🔥 Heatmaps & Rotation",
    "💰 ETF Flows",
    "🧭 Smart Money Signals",
    "📘 Capital Flow Playbook",
]

(
    tab_intraday,
    tab_comparison,
    tab_macro,
    tab_heatmaps,
    tab_flows,
    tab_signals,
    tab_playbook,
) = st.tabs(tab_labels)

with tab_intraday:
    intraday.render(
        tickers=tickers,
        avg_vol=avg_vol,
        intraday_df=intraday_df,
        price_history=price_history,
        timeframe_label=timeframe_label,
    )

with tab_comparison:
    comparison.render(
        tickers=tickers,
        price_history=price_history,
        timeframe_label=timeframe_label,
    )

with tab_macro:
    macro.render(
        assets=macro_assets,
        prices=macro_prices,
        momentum_window=momentum_window,
    )

with tab_heatmaps:
    heatmaps.render(
        assets=macro_assets,
        prices=macro_prices,
    )

with tab_flows:
    flows.render()

with tab_signals:
    signals.render(
        tickers=tickers,
        price_history=price_history,
        intraday_df=intraday_df,
        macro_prices=macro_prices,
    )

with tab_playbook:
    playbook.render()

with st.sidebar:
    if st.button("Clear Cache"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.experimental_rerun()




st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
