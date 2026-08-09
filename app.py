import streamlit as st
from datetime import datetime

from utils.data_loader import load_sector_universe, load_flow_universe
from utils.cot_loader import load_cot_positioning
from utils.fred_loader import load_fred_series
from utils.crypto_loader import load_crypto_dominance
from utils.scoring import compute_asset_scores
from utils.theming import set_page_config_and_theme, inject_custom_css

from tabs import overview, evidence, watchlist, playbook

# ---------------------------------------------------------
# PAGE CONFIG / THEME
# ---------------------------------------------------------
set_page_config_and_theme()
inject_custom_css()

st.title("💸 Money Flow Dashboard")
st.caption("Where big money is moving across asset classes — synthesized from real market data, not price momentum alone.")

# ---------------------------------------------------------
# GLOBAL DATA (drives Overview + Evidence; Watchlist loads its own)
# ---------------------------------------------------------
sector_assets, sector_prices = load_sector_universe()
flow_data = load_flow_universe()
cot_df = load_cot_positioning()
fred_df = load_fred_series()
crypto_dominance = load_crypto_dominance()

scores = compute_asset_scores(flow_data, cot_df)

as_of = None
if flow_data:
    latest_dates = [f.index[-1] for f in flow_data.values() if f is not None and not f.empty]
    if latest_dates:
        as_of = max(latest_dates).strftime("%Y-%m-%d")

# ---------------------------------------------------------
# TABS
# ---------------------------------------------------------
tab_overview, tab_evidence, tab_watchlist, tab_playbook = st.tabs(
    ["🎯 Overview", "🔍 Evidence", "📡 Watchlist", "📘 Playbook"]
)

with tab_overview:
    overview.render(scores=scores, sector_prices=sector_prices, fred_df=fred_df, as_of=as_of)

with tab_evidence:
    evidence.render(scores=scores, flow_data=flow_data, cot_df=cot_df, crypto_dominance=crypto_dominance)

with tab_watchlist:
    watchlist.render()

with tab_playbook:
    playbook.render()

with st.sidebar:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if st.button("Clear Cache"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
