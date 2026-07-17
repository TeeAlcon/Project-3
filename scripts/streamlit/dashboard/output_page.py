import streamlit as st

import utils.update_data_detection as update_data_detection

from config import (
    AES_FILE,
    SLI_MAP_FILE,
    GTS_FILE,
    EXPORT_DEC_FILE,
)


def render():
    export_dec_df = (update_data_detection.load_save(EXPORT_DEC_FILE))
    gts_sli_df = (update_data_detection.load_save(GTS_FILE))
    sli_map_df = (update_data_detection.load_save(SLI_MAP_FILE))
    gts_sli_df = gts_sli_df.rename(columns={"Shipper's ref num":"SLI"})

    if not AES_FILE.exists():
        return

    if not SLI_MAP_FILE.exists():
        return

    st.title("Output")

    st.subheader("Contact Brokers")
    broker_contact_df = (update_data_detection.build_contact_brokers_df())

    if broker_contact_df.empty:
        st.success("No ITNs currently require contacting brokers")
    else:
        st.dataframe(broker_contact_df, use_container_width=True)

    st.subheader("ITNs with duplicated SLIs")

    success, message, duplicate_slis_df = (update_data_detection.build_itns_with_duplicate_sli_list(sli_map_df))

    if not success:
        st.warning(message)
    else:
        if not duplicate_slis_df.empty:
            st.dataframe(duplicate_slis_df,use_container_width=True)
            st.warning(f"{len(duplicate_slis_df)} SLIs being duplicated in different ITNs. Contact brokers at bruce.wayne@expeditors.com")
        else:
            st.success("No ITN has duplicated SLIs with another")

    st.divider()

    st.subheader("Missing SLI in GTS-SLI")

    success, message, unmapped_sli_df = (update_data_detection.find_map_sli_not_in_gts(gts_sli_df,sli_map_df))

    if not success:
        st.warning(message)

    else:
        if not unmapped_sli_df.empty:
            st.dataframe(unmapped_sli_df,use_container_width=True)
            st.warning(f"{len(unmapped_sli_df)} SLIs are not in GTS-SLI")
        else:
            st.success("All SLIs in SLI Map are in GTS-SLI")

    st.divider()

    st.subheader("Missing SLI in Export Decleration")
    success, message, not_in_dec_sli_df = (update_data_detection.find_map_sli_not_in_export_dec(export_dec_df,sli_map_df))

    if not success:
        st.warning(message)
    else:
        if not not_in_dec_sli_df.empty:
            st.dataframe(not_in_dec_sli_df)
            st.warning(f"{len(not_in_dec_sli_df)} SLIs are not in Export Decleration")
        else:
            st.success("All SLIs in SLI Map are in GTS-SLI")

    st.divider()

    st.subheader("SAP Download List")
    sap_download_df = (update_data_detection.build_sap_download_df())

    if sap_download_df.empty:
        st.success("No ITNs currently require SAP download")
    else:
        st.dataframe(sap_download_df, use_container_width=True)
        st.warning(f"{len(sap_download_df)} AVL/SLI missing and need downloading from SAP")

    st.divider()

    st.subheader("Run Intercompany Cockpit with APL")
    build_run_intercompany_df = (update_data_detection.build_run_intercompany_cockpit())

    if build_run_intercompany_df.empty:
        st.success("No ITNs currently require running Intercompany Cockpit")
    else:
        st.dataframe(build_run_intercompany_df,use_container_width=True)
        st.warning(f"{len(build_run_intercompany_df)} ITNs need running intercompany cockpit to obtain missing AVL and SLI")