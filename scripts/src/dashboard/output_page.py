import streamlit as st
import pandas as pd

from config import (MASTER_SUMMARY_FILE, DOC_FAIL_FILE, GTS_FILE, SLI_MAP_FILE, EXPORT_DEC_FILE)

from utils.file_utils import load_save
from services import output, mapping


def render():
    summary_df = load_save(MASTER_SUMMARY_FILE)
    doc_fail_df = load_save(DOC_FAIL_FILE)
    gts_sli_df = load_save(GTS_FILE)
    sli_map_df = load_save(SLI_MAP_FILE)
    export_dec_df = load_save(EXPORT_DEC_FILE)
    
    st.title("Output")
    if not DOC_FAIL_FILE.exists() or not MASTER_SUMMARY_FILE.exists():
        st.info("Perform audit first to obtain Document Audit Fail in MASTER page")
        return
    if (DOC_FAIL_FILE.exists() and (not GTS_FILE.exists() or not SLI_MAP_FILE.exists() or not EXPORT_DEC_FILE.exists())):
        st.info("Please make sure to obtain all the file in DATA page")
        return

    # Build Outputs
    contact_broker_df = output.build_contact_brokers_df(summary_df, doc_fail_df)

    duplicate_slis_df = (mapping.build_itns_with_duplicate_sli_list(sli_map_df))

    sap_download_df = output.build_sap_download_df()

    cockpit_df = output.build_run_intercompany_cockpit_df(sli_map_df)

    unmapped_sli_df = (mapping.find_map_sli_not_in_gts(gts_sli_df,sli_map_df))

    not_in_dec_sli_df = (mapping.find_map_sli_not_in_export_dec(export_dec_df,sli_map_df))

    # Output Mapping
    outputs_map = {
        "Intercompany": cockpit_df,
        "Contact Brokers": contact_broker_df,
        "Duplicate SLIs": duplicate_slis_df,
        "SAP Download": sap_download_df,
        "Missing SLIs in GTS": unmapped_sli_df,
        "Missing SLIs in Export Dec": not_in_dec_sli_df,
    }

    # Build status pill labels
    pill_options = {}

    for label, df in outputs_map.items():

        count = len(df)

        if count > 5:
            icon = "🔴"
        elif count > 0:
            icon = "🟡"
        else:
            icon = "🟢"

        pill_options[f"{icon} {label} ({count})"] = label

    selected_pills = st.pills("Select Output(s)", options=list(pill_options.keys()), selection_mode="multi")

    # Render selected outputs only
    for pill in selected_pills:

        output_name = pill_options[pill]

        st.subheader(output_name)

        df = outputs_map[output_name]

        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.warning(f"Total ITNs/APLs/SLIs requiring action: {len(df)}")
        else:
            st.success("Process Completed")

        st.divider()