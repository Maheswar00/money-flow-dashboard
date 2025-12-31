import streamlit as st
import pandas as pd

def render(assets, prices: pd.DataFrame, momentum_window: int):
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
