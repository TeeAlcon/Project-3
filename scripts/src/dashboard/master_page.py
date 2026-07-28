import streamlit as st

from config import (AES_FILE, DOC_SEARCH_FILE, AUDIT_FILE, SEA_EXPORT_FILE, MASTER_DATA_FILE, MASTER_SUMMARY_FILE, DOC_FAIL_FILE)
from utils.file_utils import (load_save, save_csv)

import services.build_master_list
import services.document_status
import services.audit_status

from components.table_styles import (highlight_fail_rows)


def render():
    st.title("Master List")

    aes_df = load_save(AES_FILE)
    doc_df = load_save(DOC_SEARCH_FILE)
    audit_df = load_save(AUDIT_FILE)
    sea_df = load_save(SEA_EXPORT_FILE)
    if aes_df.empty:
        st.error("AES file is missing. Do not proceed until obtaining the file")
        return
    if doc_df.empty:
        st.error("Doc Search File is missing. Do not proceed until obtaining the file")
        return
    if audit_df.empty:
        st.error("Audit Doc is missing. Do not proceed until obtaining the file")
        return
    if sea_df.empty:
        st.error("Sea Export Date is missing. Do not proceed until obtaining the file")
        return
    
    # Build master list
    success, message, master_df = (services.build_master_list.build_master_list_df(aes_df, doc_df))

    if not success:
        st.error(message)
        return

    st.success(message)

    # Append Next Steps + Audit Status + Document Status columns to Master Data List
    master_df = (master_df.pipe(services.document_status.evaluate_document_status).pipe(services.audit_status.evaluate_audit_status).pipe(services.document_status.generate_next_steps))

    # Supporting tables
    doc_fail_df = (services.document_status.build_document_error_df(master_df))

    doc_fail_itns = (services.document_status.get_document_fail_itns(master_df))

    # Summary
    summary_df = (master_df[["ITN", "Document Status", "Audit Status", "Next Step"]].drop_duplicates().sort_values("ITN"))
    save_csv(summary_df, MASTER_SUMMARY_FILE)
    save_csv(master_df, MASTER_DATA_FILE)
    save_csv(doc_fail_df, DOC_FAIL_FILE)


    st.subheader("Readiness Summary")
    st.dataframe(summary_df.style.apply(highlight_fail_rows, axis=1), use_container_width=True)
    st.divider()

    st.subheader("ITNs Failing Document Audit")
    st.dataframe(doc_fail_df, use_container_width=True)
    if doc_fail_itns:
        st.warning(f"{len(doc_fail_itns)} ITNs fail document audit")
    else:
        st.success("All ITNs are document ready.")