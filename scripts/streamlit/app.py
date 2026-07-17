import streamlit as st

from dashboard import (
    data_page,
    audit_page,
    master_page,
    scrape_page,
    output_page,
)

from ui.styles import apply_styles
from components.navigation import render_navigation

PAGE_ROUTER = {
    "data": data_page.render,
    "audit": audit_page.render,
    "master": master_page.render,
    "scrape": scrape_page.render,
    "output": output_page.render,
}

def main():

    st.set_page_config(
        page_title="REPORT UPDATE",
        layout="wide"
    )

    apply_styles()

    if "page" not in st.session_state:
        st.session_state.page = "data"

    page_key = render_navigation()

    if "master_message" in st.session_state:

        msg = st.session_state.pop("master_message")

        success = st.session_state.pop("master_success",True)

        if success:
            st.success(msg)
        else:
            st.error(msg)

    # Execute selected page
    PAGE_ROUTER.get(
        page_key,
        data_page.render)()

if __name__ == "__main__":
    main()