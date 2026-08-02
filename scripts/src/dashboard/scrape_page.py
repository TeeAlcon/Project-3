import pandas as pd
import streamlit as st
from utils.file_utils import load_save
import scrape.scrape_doc

from config import MASTER_SUMMARY_FILE, AES_FILE


def render():
    st.title("Scrape ITNs for Documents")

    summary_df = (load_save(MASTER_SUMMARY_FILE))
    aes_df = (load_save(AES_FILE))

    if summary_df.empty or aes_df.empty:
        st.info("Perform audit first with input from DATA to obtain Master List in MASTER page")
        return

    scrape_df = (summary_df[summary_df["Next Step"].astype(str).str.contains( "Scrape documents", na=False)].copy().reset_index(drop=True))

    if scrape_df.empty:
        st.success("No ITNs require document scraping")
        return

    scrape_df["ITN"] = scrape_df["ITN"].astype(str).str.strip()
    aes_df["ITN"] = aes_df["ITN"].astype(str).str.strip()

    itns_need_scraping = (scrape_df["ITN"].dropna().unique().tolist())

    itn_to_ref = (aes_df.drop_duplicates("ITN").set_index("ITN")["Shipment Reference Number"])

    scrape_df["Shipment Reference Number"] = (scrape_df["ITN"].map(itn_to_ref).fillna(""))

    scraping_table = st.empty()

    scraping_table.dataframe(pd.DataFrame({"ITN": itns_need_scraping}), use_container_width=True)

    if st.button("Run scraping", use_container_width=True):
        itns_with_no_data_on_Expeditors = set(scrape.scrape_doc.run_scrape(itns_need_scraping))

        scrape_df["Status"] = (scrape_df["ITN"].isin(itns_with_no_data_on_Expeditors).map({
            True: "Not Found",
            False: "Found"
        }))

        scrape_df = scrape_df[[
            "ITN",
            "Shipment Reference Number",
            "Status"
        ]]

        scraping_table.empty()
        st.dataframe(scrape_df, use_container_width=True)

        st.success(f"Scraping completed. {len(itns_with_no_data_on_Expeditors)} ITNs with no data from Expeditors")