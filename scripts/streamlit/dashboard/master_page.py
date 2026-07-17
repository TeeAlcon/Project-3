import streamlit as st

import utils.update_data_detection as update_data_detection

from config import (
    MASTER_LIST_FILE,
)

from components.table_styles import (
    highlight_fail_rows
)


def render():
    st.title("Master List")

    # Build/refresh Master List first
    success, message, fail_match_df = (update_data_detection.build_master_list())
    if success:
        st.success(message)
    else:
        st.error(message)
        return

    master_df = update_data_detection.load_save(MASTER_LIST_FILE)
    if master_df.empty:
        st.info("Master List is empty.")
        return

    (df, doc_not_ready_df, doc_not_ready_itns, audit_ready_df,audit_ready_itns) = update_data_detection.master_list_status(master_df)

    summary_df = (df[["ITN", "Document status", "Audit status","Next Step"]].drop_duplicates().sort_values("ITN"))

    # Save summary back to Master List file
    update_data_detection.save_csv(summary_df,MASTER_LIST_FILE)

    st.subheader("Readiness Summary")

    st.dataframe(summary_df.style.apply(highlight_fail_rows,axis=1),use_container_width=True,)

    st.divider()

    st.subheader(
        "ITNs failing document audit"
    )

    st.dataframe(doc_not_ready_df,use_container_width=True)

    if doc_not_ready_itns:
        st.warning(
            f"{len(doc_not_ready_itns)} ITNs fail documents audit"
        )
    else:
        st.success( "All ITNs are ready.")

    st.subheader("Audit Ready ITNs")

    st.dataframe(audit_ready_df, use_container_width=True)
    if audit_ready_itns:
        st.success(f"{len(audit_ready_itns)} ITNs passed audit")