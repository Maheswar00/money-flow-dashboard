import streamlit as st

def render():
    st.subheader("💰 ETF Flows (Scaffolding)")

    st.info("""
This section is a scaffold for ETF flow analytics.

True ETF flow data (creations/redemptions) usually comes from:
- ETF providers
- Specialized APIs
- Institutional data vendors

You can approximate flows with:
- Change in shares outstanding × NAV
- Combined with volume and price trends.

When you're ready to plug a data source in, this tab is the place to wire it.
""")
