import streamlit as st
import pandas as pd

def render(assets, prices: pd.DataFrame, momentum_window: int, fred_df: pd.DataFrame = None):
    st.subheader("🌍 Macro Capital Flow Dashboard")
    
    # Always show what was loaded
    #st.write("Loaded macro columns:", prices.columns.tolist())
    #st.write("Missing values per asset:", prices.isna().sum())
    st.write("Latest data:", prices.tail())

    if prices is None or prices.empty:
        st.warning("No macro price data.")
        return

    rs = prices / prices.iloc[0] * 100
    momentum = prices.pct_change(momentum_window) * 100
    latest_momentum = momentum.iloc[-1].sort_values(ascending=False)

    st.markdown("### 📊 Capital Flow Overview")

    col1, col2 = st.columns([1.5, 1])

    with col1:
        st.markdown("#### 📈 Relative Strength (Indexed to 100)")
        rs_interp = rs.interpolate(method="linear")
        st.line_chart(rs_interp)

    with col2:
        st.markdown(f"#### 🔥 {momentum_window}-Day Momentum Ranking")
        st.dataframe(
            latest_momentum.to_frame("Momentum %").style.format({"Momentum %": "{:.2f}"}),
            use_container_width=True,
        )

    st.markdown("""
**Interpretation:**
- Top assets in the momentum list are attracting capital.
- Rising RS + positive momentum → strong institutional interest.
- Falling RS + negative momentum → distribution / outflows.
""")

    st.markdown("### 💧 Liquidity Conditions")
    st.caption("Capital follows liquidity. This is the actual data behind that idea, not just the theory.")

    if fred_df is None or fred_df.empty:
        st.info("Liquidity data (FRED) unavailable right now.")
        return

    latest = fred_df.iloc[-1]
    prior_month = fred_df[fred_df.index <= fred_df.index[-1] - pd.Timedelta(days=30)]
    prior = prior_month.iloc[-1] if not prior_month.empty else fred_df.iloc[0]

    dollar_cols = [c for c in fred_df.columns if "$B" in c]
    pct_cols = [c for c in fred_df.columns if "%" in c]

    lcol1, lcol2 = st.columns([1.5, 1])

    with lcol1:
        if dollar_cols:
            liquidity_indexed = fred_df[dollar_cols] / fred_df[dollar_cols].iloc[0] * 100
            st.line_chart(liquidity_indexed)
            st.caption("Indexed to 100 at the start of the loaded window, so series with very different scales (trillions vs billions) are visually comparable.")

    with lcol2:
        for col in dollar_cols + pct_cols:
            change = latest[col] - prior[col]
            st.metric(
                label=col,
                value=f"{latest[col]:,.2f}",
                delta=f"{change:+,.2f} (~30d)",
            )

    st.markdown("""
**Interpretation:**
- Fed balance sheet expanding + reverse repo draining → liquidity entering the system → tailwind for risk assets.
- M2 growth accelerating → more capital available to chase returns.
- Rising 10Y yield → tighter financial conditions, often a headwind for growth stocks and crypto.
""")
