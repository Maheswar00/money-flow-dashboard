import pandas as pd
import plotly.express as px
import streamlit as st

from utils.theming import flow_card_html

LIQUIDITY_META = {
    "Fed Balance Sheet ($B)": {"up_is_good": True, "rising": "Expanding", "falling": "Draining"},
    "ON Reverse Repo ($B)": {"up_is_good": False, "rising": "Refilling", "falling": "Draining"},
    "M2 Money Supply ($B)": {"up_is_good": True, "rising": "Growing", "falling": "Shrinking"},
    "10Y Treasury Yield (%)": {"up_is_good": False, "rising": "Rising", "falling": "Falling"},
}


def _render_scorecard(scores: list):
    if not scores:
        st.warning("No asset-class data available right now.")
        return

    cols_per_row = 4
    for i in range(0, len(scores), cols_per_row):
        row = scores[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, entry in zip(cols, row):
            with col:
                st.markdown(
                    flow_card_html(entry["label"], entry["verdict"], entry["score"], entry["reason"]),
                    unsafe_allow_html=True,
                )


def _render_sector_strip(sector_prices: pd.DataFrame):
    st.markdown("#### Sector Rotation (Inside Equities)")
    st.caption("20-day return by S&P 500 sector — where money is rotating *within* stocks, not just across asset classes.")

    if sector_prices is None or sector_prices.empty or len(sector_prices) < 21:
        st.info("Not enough sector data yet.")
        return

    returns = (sector_prices.pct_change(20).iloc[-1] * 100).sort_values()
    df = returns.reset_index()
    df.columns = ["Sector", "20D Return %"]

    bound = max(5.0, float(df["20D Return %"].abs().max()) * 1.1)
    fig = px.bar(
        df, x="20D Return %", y="Sector", orientation="h",
        color="20D Return %",
        color_continuous_scale=["#e34948", "#f0efec", "#2a78d6"],
        range_color=[-bound, bound],
    )
    fig.update_layout(height=320, showlegend=False, coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True, key="overview_sector_bar")


def _render_liquidity_strip(fred_df: pd.DataFrame):
    st.markdown("#### Liquidity Backdrop")
    st.caption("Capital follows liquidity — the macro conditions behind everything above.")

    if fred_df is None or fred_df.empty:
        st.info("Liquidity data unavailable right now.")
        return

    latest = fred_df.iloc[-1]
    prior_window = fred_df[fred_df.index <= fred_df.index[-1] - pd.Timedelta(days=30)]
    prior = prior_window.iloc[-1] if not prior_window.empty else fred_df.iloc[0]

    cards = []
    for col in fred_df.columns:
        meta = LIQUIDITY_META.get(col, {"up_is_good": True, "rising": "Rising", "falling": "Falling"})
        change = latest[col] - prior[col]
        # Some series (M2) are monthly - a 30-day lookback can land on the
        # same reading with no new print yet. Treat that as flat, not "falling".
        flat = abs(change) < (abs(latest[col]) * 1e-6 if latest[col] else 1e-9)

        if flat:
            color, status, arrow = "#898781", "Flat (no new reading yet)", "►"
        else:
            rising = change > 0
            good = rising == meta["up_is_good"]
            color = "#0ca30c" if good else "#d03b3b"
            status = meta["rising"] if rising else meta["falling"]
            arrow = "▲" if rising else "▼"
        cards.append(
            f"""<div class="liquidity-item">
                <div class="liquidity-label">{col}</div>
                <div class="liquidity-value">{latest[col]:,.2f}</div>
                <div class="liquidity-delta" style="color:{color}">{arrow} {status} ({change:+,.2f} / 30d)</div>
            </div>"""
        )

    st.markdown(f'<div class="liquidity-strip">{"".join(cards)}</div>', unsafe_allow_html=True)


def render(scores: list, sector_prices: pd.DataFrame, fred_df: pd.DataFrame, as_of: str = None):
    st.subheader("Where Is Money Flowing")
    if as_of:
        st.caption(f"As of {as_of} · verdicts blend price/volume pressure, dollar-flow direction, and institutional futures positioning")

    _render_scorecard(scores)

    st.divider()

    col1, col2 = st.columns([1, 1])
    with col1:
        _render_sector_strip(sector_prices)
    with col2:
        _render_liquidity_strip(fred_df)

    with st.expander("How the verdict is calculated"):
        st.markdown("""
Each asset class gets a score from **-1 (strong outflow) to +1 (strong inflow)**, a weighted blend of:

- **Chaikin Money Flow (35%)** — whether price is closing near the top or bottom of its daily range, weighted by volume
- **20-day dollar-flow ratio (35%)** — net signed dollar volume (up-day volume minus down-day volume) as a fraction of total dollar volume traded
- **Money Flow Index (15%)** — volume-weighted RSI; mainly flags overbought/oversold extremes
- **CFTC institutional positioning (15%)** — whether large speculators are net long/short and adding/trimming this week (skipped, and weights rebalanced, for assets with no CFTC futures match — currently Ethereum)

Score ≥ +0.15 → **Inflow**. Score ≤ -0.15 → **Outflow**. In between → **Neutral**.
This is a transparent heuristic built from real market data, not a prediction —
see the Evidence tab for the raw numbers behind any card.
""")
