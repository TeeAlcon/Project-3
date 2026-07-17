import pandas as pd
import streamlit as st

import scrape.scrape_doc
import utils.update_data_detection as update_data_detection

from config import MASTER_LIST_FILE


def render():
    st.title("Scrape ITNs for Documents")

    master_df = (update_data_detection.load_save(MASTER_LIST_FILE))

    if master_df.empty:
        st.info("Perform audit first to obtain Master List")
        return

    scrape_df = (master_df[master_df["Next Step"].astype(str).str.contains( "Scrape documents",na=False)].copy().reset_index(drop=True))

    itns_need_scraping = (scrape_df["ITN"].astype(str).str.strip().dropna().unique().tolist())

    scraping_table = st.empty()

    scraping_table.dataframe(pd.DataFrame({"ITN": itns_need_scraping}), use_container_width=True)

    if st.button("Run scraping", use_container_width=True):
        itns_with_no_data_on_Expeditors = (scrape.scrape_doc.run_scrape(itns_need_scraping))
        scraping_table.dataframe(pd.DataFrame({"ITN":itns_with_no_data_on_Expeditors}),use_container_width=True)

        st.success("Scraping completed. The above list is ITNs that were not found from Expeditors data")