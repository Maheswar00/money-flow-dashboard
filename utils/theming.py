import streamlit as st

def set_page_config_and_theme():
    st.set_page_config(
        page_title="Money Flow Dashboard",
        layout="wide",
    )
    # Theme is controlled via .streamlit/config.toml.
    # This helper is here if you want to add runtime CSS later.
