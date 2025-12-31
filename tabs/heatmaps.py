import streamlit as st
import pandas as pd
import plotly.express as px

def _build_return_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    periods_map = {
        "1D": 1,
        "1W": 5,
        "1M": 21,
        "3M": 63,
        "6M": 126,
        "1Y": 252,
    }
    out = {}
    for label, periods in periods_map.items():
        out[label] = prices.pct_change(periods=periods).iloc[-1] * 100
    return pd.DataFrame(out)

def render(assets, prices: pd.DataFrame):
    st.subheader("🔥 Heatmaps & Rotation")

    if prices is None or prices.empty:
        st.warning("No macro price data for heatmaps.")
        return

    returns = _build_return_matrix(prices).round(2)
    st.markdown("### 📌 Multi‑Period Return Heatmap")

    fig_ret = px.imshow(
        returns,
        text_auto=True,
        color_continuous_scale="RdYlGn",
        aspect="auto",
        labels=dict(x="Period", y="Asset", color="% Return"),
    )
    st.plotly_chart(fig_ret, use_container_width=True, key="heatmap_returns")

    st.markdown("### ⚡ Momentum Heatmap (Short vs Long)")

    momentum_short = prices.pct_change(20).iloc[-1] * 100
    momentum_long = prices.pct_change(60).iloc[-1] * 100
    mom_df = pd.concat(
        [momentum_short.rename("20D"), momentum_long.rename("60D")],
        axis=1,
    ).round(2)

    fig_mom = px.imshow(
        mom_df,
        text_auto=True,
        color_continuous_scale="RdYlGn",
        aspect="auto",
        labels=dict(x="Window", y="Asset", color="% Momentum"),
    )
    st.plotly_chart(fig_mom, use_container_width=True, key="heatmap_momentum")

    st.markdown("""
**Use case:**
- Look for clusters of green → capital concentrating.
- Watch for assets flipping from red to green across horizons → early rotation.
""")
