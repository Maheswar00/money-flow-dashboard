import streamlit as st

from utils.data_loader import load_sector_universe, load_flow_universe
from utils.cot_loader import load_cot_positioning
from utils.fred_loader import load_fred_series
from utils.crypto_loader import load_crypto_dominance
from utils.scoring import compute_asset_scores
from utils.theming import set_page_config_and_theme, inject_custom_css
from utils.freshness import get_freshness, format_age

from tabs import overview, evidence, watchlist, playbook

# ---------------------------------------------------------
# PAGE CONFIG / THEME
# ---------------------------------------------------------
set_page_config_and_theme()
inject_custom_css()

header_col, refresh_col = st.columns([5, 1])
with header_col:
    st.title("💸 Money Flow Dashboard")
    st.caption("Where big money is moving across asset classes — synthesized from real market data, not price momentum alone.")
with refresh_col:
    st.write("")
    st.write("")
    if st.button("🔄 Refresh Data", use_container_width=True, help="Data is cached, not live — this forces an immediate re-fetch of everything below."):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

_freshness_bits = [f"{tier['label']}: fetched {format_age(tier['fetched_at'])} (refreshes every {tier['ttl']})" for tier in get_freshness()]
st.caption("This is **not real-time** — " + " · ".join(_freshness_bits) + ". Click Refresh Data for the latest right now.")

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
