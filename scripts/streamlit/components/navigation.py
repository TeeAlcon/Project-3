import streamlit as st

def render_navigation():
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("Data", use_container_width=True):
            st.session_state.page = "data"

    with col2:
        if st.button("Build Audit Doc", use_container_width=True):
            st.session_state.page = "audit"

    with col3:
        if st.button("Master", use_container_width=True):
            st.session_state.page = "master"

    with col4:
        if st.button("Scrape Missing Doc", use_container_width=True):
            st.session_state.page = "scrape"

    with col5:
        if st.button("Output", use_container_width=True):
            st.session_state.page = "output"

    return st.session_state.page