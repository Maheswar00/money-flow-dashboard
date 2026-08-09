import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.indicators import chaikin_money_flow, money_flow_index, on_balance_volume, dollar_volume
from utils.scoring import COT_MATCH, _WEIGHTS, window_label
from utils.theming import verdict_badge_html


def _rolling_flow_ratio(close: pd.Series, volume: pd.Series, window: int) -> pd.Series:
    """Same math as utils.indicators.net_flow_ratio, but as a time series
    instead of a single latest value - for the trend chart."""
    dv = dollar_volume(close, volume)
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    signed = direction * dv
    return signed.rolling(window).sum() / dv.rolling(window).sum()


def _component_breakdown(entry: dict, frame: pd.DataFrame):
    idx = frame.index if frame is not None else None
    rows = [
        {"Component": "Chaikin Money Flow", "Window": window_label(idx, 20) or "—", "Value": f"{entry['cmf']:+.3f}", "Weight": f"{_WEIGHTS['cmf']:.0%}", "Scored?": "Yes"},
        {"Component": "20D dollar-flow ratio", "Window": entry.get("window_20d") or "—", "Value": f"{entry['flow_ratio_20d']:+.3f}", "Weight": f"{_WEIGHTS['flow_ratio']:.0%}", "Scored?": "Yes"},
        {"Component": "5D dollar-flow ratio", "Window": entry.get("window_5d") or "—", "Value": f"{entry['flow_ratio_5d']:+.3f}" if entry.get("flow_ratio_5d") == entry.get("flow_ratio_5d") else "n/a", "Weight": "—", "Scored?": "No — shown for context only"},
        {"Component": "Money Flow Index", "Window": window_label(idx, 14) or "—", "Value": f"{entry['mfi']:.1f}", "Weight": f"{_WEIGHTS['mfi']:.0%}", "Scored?": "Yes"},
    ]
    if entry["has_cot"]:
        cot_val = "n/a" if entry["cot_component"] is None else f"{entry['cot_component']:+.2f}"
        rows.append({"Component": "CFTC institutional positioning", "Window": "most recent weekly report", "Value": cot_val, "Weight": f"{_WEIGHTS['cot']:.0%}", "Scored?": "Yes"})
    else:
        rows.append({"Component": "CFTC institutional positioning", "Window": "—", "Value": "no futures match", "Weight": "excluded", "Scored?": "No"})
    return pd.DataFrame(rows)


def render(scores: list, flow_data: dict, cot_df: pd.DataFrame, crypto_dominance: dict = None):
    st.subheader("Evidence")
    st.caption("Pick an asset class to see the raw signals behind its Overview verdict.")

    if not scores:
        st.warning("No asset-class data available right now.")
        return

    labels = [s["label"] for s in scores]
    selected_label = st.selectbox("Asset class:", labels)
    entry = next(s for s in scores if s["label"] == selected_label)
    frame = (flow_data or {}).get(selected_label)

    badge_col, score_col = st.columns([1, 3])
    with badge_col:
        st.markdown(verdict_badge_html(entry["verdict"]), unsafe_allow_html=True)
    with score_col:
        st.write(entry["reason"])
        if entry.get("trend") == "reversing":
            st.warning(
                f"5D flow ({entry.get('window_5d')}) and 20D flow ({entry.get('window_20d')}) disagree — "
                "the verdict above is the 20D read and may be lagging a more recent reversal.",
                icon="⚠️",
            )

    st.markdown("#### Score breakdown")
    st.caption("Every row shows exactly what date range it covers — nothing here is a single unlabeled number.")
    st.dataframe(_component_breakdown(entry, frame), use_container_width=True, hide_index=True)

    if frame is None or frame.empty:
        st.info("No price/volume history available for this asset.")
        return

    high, low, close, volume = frame["High"], frame["Low"], frame["Close"], frame["Volume"]

    st.markdown("#### Price, with money-flow overlays")
    cmf_series = chaikin_money_flow(high, low, close, volume)
    mfi_series = money_flow_index(high, low, close, volume)
    ratio_series = _rolling_flow_ratio(close, volume, 20)
    obv_series = on_balance_volume(close, volume)

    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=close.index, y=close, name="Close", line=dict(width=2, color="#2a78d6")))
    fig_price.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Price", hovermode="x unified")
    st.plotly_chart(fig_price, use_container_width=True, key="evidence_price")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Chaikin Money Flow (20)**")
        st.caption("Above 0 = buying pressure, below 0 = selling pressure.")
        fig_cmf = go.Figure()
        fig_cmf.add_trace(go.Scatter(x=cmf_series.index, y=cmf_series, line=dict(width=2, color="#1baf7a")))
        fig_cmf.add_hline(y=0, line_color="rgba(128,128,128,0.4)")
        fig_cmf.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified")
        st.plotly_chart(fig_cmf, use_container_width=True, key="evidence_cmf")

    with c2:
        st.markdown("**Money Flow Index (14)**")
        st.caption("Above 80 = overbought, below 20 = oversold.")
        fig_mfi = go.Figure()
        fig_mfi.add_trace(go.Scatter(x=mfi_series.index, y=mfi_series, line=dict(width=2, color="#eda100")))
        fig_mfi.add_hline(y=80, line_dash="dot", line_color="rgba(208,59,59,0.5)")
        fig_mfi.add_hline(y=20, line_dash="dot", line_color="rgba(12,163,12,0.5)")
        fig_mfi.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=0), yaxis_range=[0, 100], hovermode="x unified")
        st.plotly_chart(fig_mfi, use_container_width=True, key="evidence_mfi")

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**20D Dollar-Flow Ratio**")
        st.caption("Net signed dollar volume ÷ total dollar volume, rolling 20 days.")
        fig_ratio = go.Figure()
        fig_ratio.add_trace(go.Scatter(x=ratio_series.index, y=ratio_series, line=dict(width=2, color="#4a3aa7")))
        fig_ratio.add_hline(y=0, line_color="rgba(128,128,128,0.4)")
        fig_ratio.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified")
        st.plotly_chart(fig_ratio, use_container_width=True, key="evidence_ratio")

    with c4:
        st.markdown("**On-Balance Volume (cumulative)**")
        st.caption("Running total of volume, added on up days and subtracted on down days.")
        fig_obv = go.Figure()
        fig_obv.add_trace(go.Scatter(x=obv_series.index, y=obv_series, line=dict(width=2, color="#e87ba4")))
        fig_obv.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified")
        st.plotly_chart(fig_obv, use_container_width=True, key="evidence_obv")

    if entry["has_cot"]:
        st.markdown("#### Institutional Positioning (CFTC COT)")
        market = COT_MATCH.get(selected_label)
        if cot_df is not None and not cot_df.empty and market:
            hist = cot_df[cot_df["Label"] == market].sort_values("Date")
        else:
            hist = pd.DataFrame()

        if hist.empty:
            st.info("COT data unavailable right now.")
        else:
            fig_cot = go.Figure()
            colors = ["#0ca30c" if v >= 0 else "#d03b3b" for v in hist["NetPosition"]]
            fig_cot.add_trace(go.Bar(x=hist["Date"], y=hist["NetPosition"], marker_color=colors))
            fig_cot.add_hline(y=0, line_color="rgba(128,128,128,0.4)")
            fig_cot.update_layout(height=240, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Net large-spec position")
            st.plotly_chart(fig_cot, use_container_width=True, key="evidence_cot")
            st.caption("Positive = large speculators net long. Negative = net short. Source: CFTC Commitments of Traders, weekly.")
    else:
        st.caption(f"No CFTC futures market matches {selected_label} — institutional positioning isn't available for this asset.")

    if selected_label in ("Bitcoin", "Ethereum") and crypto_dominance and crypto_dominance.get("btc_dominance") is not None:
        st.markdown("#### Crypto Rotation Context")
        d1, d2, d3 = st.columns(3)
        d1.metric("BTC Dominance", f"{crypto_dominance['btc_dominance']:.1f}%")
        d2.metric("ETH Dominance", f"{crypto_dominance['eth_dominance']:.1f}%")
        total_cap = crypto_dominance.get("total_market_cap_usd")
        d3.metric("Total Crypto Market Cap", f"${total_cap / 1e9:,.0f}B" if total_cap else "—")
        st.caption("Rising BTC dominance → capital rotating from altcoins into Bitcoin. Falling → capital moving into altcoins.")
    else:
        st.caption(f"No CFTC futures market matches {selected_label} — institutional positioning isn't available for this asset.")
