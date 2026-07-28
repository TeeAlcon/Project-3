import pandas as pd
import streamlit as st
from utils.file_utils import load_save
import scrape.scrape_doc

from config import MASTER_SUMMARY_FILE


def render():
    st.title("Scrape ITNs for Documents")

    summary_df = (load_save(MASTER_SUMMARY_FILE))

    if summary_df.empty:
        st.info("Perform audit first to obtain Master List in MASTER page")
        return

    scrape_df = (summary_df[summary_df["Next Step"].astype(str).str.contains( "Scrape documents", na=False)].copy().reset_index(drop=True))

    itns_need_scraping = (scrape_df["ITN"].astype(str).str.strip().dropna().unique().tolist())

    scraping_table = st.empty()

    scraping_table.dataframe(pd.DataFrame({"ITN": itns_need_scraping}), use_container_width=True)

    if st.button("Run scraping", use_container_width=True):
        itns_with_no_data_on_Expeditors = (scrape.scrape_doc.run_scrape(itns_need_scraping))
        scraping_table.dataframe(pd.DataFrame({"ITN":itns_with_no_data_on_Expeditors}),use_container_width=True)

        st.success("Scraping completed. The above list is ITNs that were not found from Expeditors data")