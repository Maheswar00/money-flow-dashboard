import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.indicators import dollar_volume


def _flow_metrics(frame: pd.DataFrame, window: int):
    """Net signed dollar flow over the trailing window, plus that flow as a
    fraction of total dollar volume traded (bounded [-1, 1], comparable across
    assets regardless of price/size - unlike the raw dollar figure)."""
    close, volume = frame["Close"], frame["Volume"]
    dv = dollar_volume(close, volume)
    direction = np.sign(close.diff().fillna(0))
    signed = (direction * dv).tail(window)
    total = dv.tail(window).sum()

    net_flow = signed.sum()
    ratio = net_flow / total if total else np.nan
    return net_flow, ratio


def _build_flow_table(flow_data: dict) -> pd.DataFrame:
    rows = []
    for label, frame in flow_data.items():
        if frame is None or len(frame) < 21:
            continue
        net_5d, ratio_5d = _flow_metrics(frame, 5)
        net_20d, ratio_20d = _flow_metrics(frame, 20)
        rows.append({
            "Asset": label,
            "5D Net $ Flow": net_5d,
            "5D Flow Ratio": ratio_5d,
            "20D Net $ Flow": net_20d,
            "20D Flow Ratio": ratio_20d,
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("20D Flow Ratio", ascending=False)


def render(flow_data: dict = None, crypto_dominance: dict = None):
    st.subheader("💰 Money Flow (Dollar-Volume Proxy)")

    st.info(
        "True ETF creation/redemption data (the actual definition of 'ETF flows') and on-chain exchange "
        "netflow/stablecoin-supply data require paid vendors (ETF.com/Lipper/EPFR, Glassnode/CryptoQuant) and "
        "aren't included here. What follows is the best **free** proxy: net dollar volume, signed by each day's "
        "price direction, as a fraction of total dollar volume traded - a rough read on whether buying or selling "
        "is dominating each asset class."
    )

    st.markdown("### 📊 Net Dollar Flow by Asset Class")

    table = _build_flow_table(flow_data or {})

    if table.empty:
        st.warning("No flow data available right now.")
    else:
        st.dataframe(
            table.style.format({
                "5D Net $ Flow": "${:,.0f}",
                "5D Flow Ratio": "{:+.1%}",
                "20D Net $ Flow": "${:,.0f}",
                "20D Flow Ratio": "{:+.1%}",
            }),
            use_container_width=True,
        )

        fig = px.bar(
            table.sort_values("20D Flow Ratio"),
            x="20D Flow Ratio",
            y="Asset",
            orientation="h",
            color="20D Flow Ratio",
            color_continuous_scale="RdYlGn",
            range_color=[-0.5, 0.5],
        )
        fig.update_layout(height=350, xaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True, key="flows_ratio_bar")

        st.caption(
            "Flow Ratio = (net signed dollar volume) / (total dollar volume) over the window. "
            "Near +100% → almost all volume came on up days (persistent buying). Near -100% → almost all volume came on down days (persistent selling)."
        )

    st.markdown("### ₿ Crypto Rotation: Bitcoin Dominance")

    if not crypto_dominance or crypto_dominance.get("btc_dominance") is None:
        st.info("Crypto dominance data unavailable right now.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("BTC Dominance", f"{crypto_dominance['btc_dominance']:.1f}%")
        c2.metric("ETH Dominance", f"{crypto_dominance['eth_dominance']:.1f}%")
        total_cap = crypto_dominance.get("total_market_cap_usd")
        change_24h = crypto_dominance.get("market_cap_change_pct_24h")
        c3.metric(
            "Total Crypto Market Cap",
            f"${total_cap / 1e9:,.0f}B" if total_cap else "—",
            f"{change_24h:+.1f}% (24h)" if change_24h is not None else None,
        )
        st.caption(
            "Rising BTC dominance → capital rotating from altcoins into Bitcoin (risk-off within crypto). "
            "Falling dominance → capital moving into altcoins (risk-on within crypto)."
        )
