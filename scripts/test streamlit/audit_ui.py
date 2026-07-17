import pandas as pd
import streamlit as st
import streamlit.utils.update_data_detection as update_data_detection 
import streamlit.scrape.scrape_doc

from pathlib import Path


AES_FILE = Path("Drawback Report") / "AES Report.csv"
GTS_FILE = Path("Drawback Report") / "GTS SLI.csv"
SLI_MAP_FILE = Path("Drawback Report") / "SLI Map.csv"
SEA_EXPORT_FILE = Path("Drawback Report") / "Sea Export Date.csv"
DOC_SEARCH_FILE = Path("Drawback Report") / "Doc Search.csv"
AUDIT_DOC_FILE = Path("Drawback Report") / "Audit Doc.csv"
MASTER_LIST_FILE = Path("Drawback Report") / "Master List.csv"
EXPORT_DEC_FILE = Path("Drawback Report") / "Export Dec.csv"
Path("Drawback Report").mkdir(parents=True, exist_ok=True)

ID_COLS = {   
    AES_FILE: "ITN",
    GTS_FILE: "Shipper's ref num",
    SLI_MAP_FILE: "ITN",
    SEA_EXPORT_FILE: "ITN",
    DOC_SEARCH_FILE: "ITN",
    AUDIT_DOC_FILE: "ITN",
    EXPORT_DEC_FILE: "Number",
}

def data_page():
    st.title("Data Import")

    IMPORT_FILES = {
        "aes": ("AES Report", AES_FILE),
        "gts": ("GTS-SLI", GTS_FILE),
        "sli_map": ("SLI Map", SLI_MAP_FILE),
        "sea_export": ("Sea Export", SEA_EXPORT_FILE),
        "doc_search": ("Doc Search", DOC_SEARCH_FILE),
        "audit_doc": ("Audit Doc", AUDIT_DOC_FILE),
        "export_dec": ("Export Dec", EXPORT_DEC_FILE)
    }

    status = []

    for key, (label, path) in IMPORT_FILES.items():
        df = update_data_detection.load_save(path)

        status.append({
            "Report": label,
            "Loaded": "Yes" if path.exists() else "No",
            "Rows": len(df),
            "Columns": len(df.columns),
        })

    st.subheader("Current Status")
    st.dataframe(pd.DataFrame(status), use_container_width=True)

    report_key = st.selectbox(
        "Select report",
        list(IMPORT_FILES.keys()),
        format_func=lambda x: IMPORT_FILES[x][0],
    )

    title, base_file = IMPORT_FILES[report_key]

    st.divider()

    document_page(title, base_file)

def document_page(title, base_file):
    st.title(title)

    save_df = update_data_detection.load_save(base_file)
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"], key=title)

    if uploaded_file:
        import_df = update_data_detection.clean_columns(update_data_detection.read_csv(uploaded_file))
        valid, message = update_data_detection.validate_report_structure(import_df, base_file)
        if not valid:
            st.error(message)
            st.stop()

        id_col = ID_COLS[base_file]

        if id_col in import_df.columns:
            import_df[id_col] = import_df[id_col].astype(str).str.strip().str.replace(r"\s+", "", regex=True)

        if save_df.empty and not base_file.exists():
            update_data_detection.save_csv(import_df, base_file)
            st.success("Initial file saved.")
            st.rerun()

        if st.button("Analyze report", type="primary", key=title + "_analyze"):
            try:
                updated_df, rows_added = update_data_detection.analyze_import(save_df, import_df, id_col)
                st.session_state[title + "_data"] = (updated_df, rows_added)
            except ValueError as e:
                st.error(str(e))

    # Preview change
    if title + "_data" in st.session_state:
        updated_df, rows_added = st.session_state[title + "_data"] # updated_df and rows_added are being saved as aes_data

        tabs = st.tabs(["Rows added", "Final save preview"])

        with tabs[0]:
            st.dataframe(rows_added, use_container_width=True)

        with tabs[1]:
            st.dataframe(updated_df, use_container_width=True)

        if rows_added.empty:
            st.info("No change found")

        if st.button(f"Save update to {title}", type="primary", key=title + "_save"):
            update_data_detection.save_csv(updated_df, base_file)
            st.success("Save updated")

    # Reset button
    if base_file.exists():
        st.subheader("Current saved preview")
        st.dataframe(update_data_detection.load_save(base_file), height=500, use_container_width=True)

        if st.button("Reset", key=title + "_reset"):
            base_file.unlink(missing_ok=True)

            # Clear only this page's session data instead of everything
            st.session_state.pop(title + "_data", None)

            st.rerun()

def highlight_fail_rows(row):
    value_fail = (
        "Value Audit" in row.index
        and row["Value Audit"] == "FAIL"
    ) 
    qty_fail = (
        "Qty Diff" in row.index
        and row["Qty Audit"] == "FAIL"
    )
    audit_fail = (
        "Audit status" in row.index
        and row["Audit status"] == "FAIL"
    )
    doc_fail = (
        "Document status" in row.index
        and row["Document status"] == "FAIL"
    )
    if value_fail or qty_fail or doc_fail or audit_fail:
        return["background-color: #8B0000"] * len(row)
    return [""] * len(row)


# UI. Start here
def main():
    st.set_page_config(page_title="REPORT UPDATE", layout="wide")

    # Optional: hide Streamlit UI
    st.markdown("""
    <style>

    :root {
        --text-color: hsla(210, 50%, 95%, 1);
        --shadow-color: hsla(210, 40%, 52%, .4);
        --btn-color: #0505A9;
    }

    div.stButton > button {

        position: relative;
        overflow: hidden;

        width: 100%;
        padding: 12px 20px;

        border: none;
        border-radius: 8px;

        font-weight: 900;
        text-transform: uppercase;

        color: var(--text-color);
        background-color: var(--btn-color);

        box-shadow: var(--shadow-color) 2px 2px 22px;

        transition:
            transform 0.25s ease,
            box-shadow 0.25s ease,
            background-color 0.25s ease;
    }

    /* Floating bubbles */
    div.stButton > button::before {
        content: "";

        position: absolute;
        top: 0;
        left: 0;

        width: 100%;
        height: 300%;

        opacity: 0.6;
        pointer-events: none;

        background:
            radial-gradient(circle at 20% 35%,
            transparent 0,
            transparent 2px,
            white 3px,
            white 4px,
            transparent 4px),

            radial-gradient(circle at 75% 44%,
            transparent 0,
            transparent 2px,
            white 3px,
            white 4px,
            transparent 4px),

            radial-gradient(circle at 46% 52%,
            transparent 0,
            transparent 4px,
            white 5px,
            white 6px,
            transparent 6px);

        animation: bubbles 5s linear infinite;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 25px rgba(0,120,255,.6);}

    div.stButton > button:active {
        transform: scale(0.98);}

    div.stButton > button:focus {
        outline: none;
        box-shadow: 0 0 30px rgba(0,120,255,.8);}

    @keyframes bubbles {
        from {
        transform: translateY(0);
        }

        to {
        transform: translateY(-66%);
        }
    }

    </style>
    """, unsafe_allow_html=True)

    MASTER_PAGE = {
        "master": ("Master List", MASTER_LIST_FILE)
    }

    if "page" not in st.session_state:
        st.session_state.page = "data"

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("Data", use_container_width = True):
            st.session_state.page = "data"

    with col2:
        if st.button("Build Audit Doc", use_container_width = True):
            st.session_state.page = "audit"
            st.rerun()

    with col3:
        if st.button("Master", use_container_width = True):
            success, message, fail_match_df = update_data_detection.build_master_list()

            st.session_state["master_message"] = message
            st.session_state["master_success"] = success
            st.session_state["fail_match_df"] = fail_match_df

            st.session_state.page = "master"
            st.rerun()
    
    with col4:
        if st.button("Scrape Missing Doc", use_container_width = True):
            st.session_state.page = "scrape"
            st.rerun()
    
    with col5:
        if st.button("Output", use_container_width = True):
            st.session_state.page = "output"
            st.rerun()

    if "master_message" in st.session_state:
        msg = st.session_state.pop("master_message")
        success = st.session_state.pop("master_success", True)

        if success:
            st.success(msg)
        else:
            st.error(msg)
    page_key = st.session_state.page

    aes_df = update_data_detection.load_save(AES_FILE)
    gts_sli_df =  update_data_detection.load_save(GTS_FILE)
    sli_map_df = update_data_detection.load_save(SLI_MAP_FILE)
    master_df = update_data_detection.load_save(MASTER_LIST_FILE)

    if page_key == "data":
        data_page()

    elif page_key in MASTER_PAGE:
        title, base_file = MASTER_PAGE[page_key]
        st.title(title)

        master_df = update_data_detection.load_save(base_file)

        if master_df.empty:
            st.info("Master List is empty.")
        else:
            gts_sli_df = gts_sli_df.rename(columns= {"Shipper's ref num": "SLI"})

            df, doc_not_ready_df, doc_not_ready_itns, audit_ready_df, audit_ready_itns = update_data_detection.master_list_status(master_df)
            summary_df = (df[["ITN", "Document status", "Audit status", "Next Step"]].drop_duplicates())
            update_data_detection.save_csv(summary_df, MASTER_LIST_FILE) # Save Master List   

            st.subheader("Readiness Summary")
            st.dataframe(summary_df.style.apply(highlight_fail_rows, axis=1), use_container_width=True)
            st.divider()

            st.subheader("ITNs failling document audit")
            st.dataframe(doc_not_ready_df, use_container_width=True)
            if doc_not_ready_itns:
                st.warning(f"{len(doc_not_ready_itns)} ITNs fail documents audit")
            else:
                st.success("All ITNs are ready.")

    elif page_key == "audit":
        st.title("Audit Doc Generator")
        gts_sli_df = gts_sli_df.rename(columns={"Shipper's ref num": "SLI"})

        success, message, audit_df = update_data_detection.build_audit_summary_df(aes_df, gts_sli_df, sli_map_df)
        if not success:
            st.error(message)
        else:
            update_data_detection.save_csv(audit_df, AUDIT_DOC_FILE)
            st.success(message)
            st.dataframe(audit_df.style.apply(highlight_fail_rows, axis=1), use_container_width = True)


    elif page_key == "scrape":
        st.title("Scrape ITNs for Documents")
        if master_df.empty:
            st.info("Perform audit first to obtain Master List")
        else:
            scrape_df = (master_df[master_df["Next Step"].astype(str).str.contains("Scrape documents", na=False)].copy().reset_index(drop=True))
            itns_need_scraping = (scrape_df["ITN"].astype(str).str.strip().dropna().unique().tolist())
            scraping_table = st.empty()
            scraping_table.dataframe(pd.DataFrame({"ITN": itns_need_scraping}), use_container_width=True)
            if st.button("Run scraping", use_container_width=True):
                itns_with_no_data_on_Expeditors = streamlit.scrape.scrape_doc.run_scrape(itns_need_scraping)
                scraping_table.dataframe(pd.DataFrame({"ITN": itns_with_no_data_on_Expeditors}), use_container_width = True)
                st.success("Scraping completed. The above list is ITNs that were not found from Expeditors data")

    elif page_key == "output":
        # Please obtain Master List first
        export_dec_df = update_data_detection.load_save(EXPORT_DEC_FILE)
        gts_sli_df = gts_sli_df.rename(columns = {"Shipper's ref num": "SLI"})

        if not AES_FILE.exists():
            return False
        if not SLI_MAP_FILE.exists():
            return False

        st.title("Output")

        st.subheader("Contact Brokers")
        broker_contact_df = update_data_detection.build_contact_brokers_df()
        if broker_contact_df.empty:
            st.success("No ITNs currently require contacting brokers")
        else:
            st.dataframe(broker_contact_df, use_container_width=True)
        
        st.subheader("ITNs with duplicated SLIs")
        success, message, duplicate_slis_df = update_data_detection.build_itns_with_duplicate_sli_list(sli_map_df)
        if not success:
            st.warning(message)
        else:
            if not duplicate_slis_df.empty:
                st.dataframe(duplicate_slis_df, use_container_width=True)
                st.warning(f"{len(duplicate_slis_df)} SLIs being duplicated in different ITNs. Contact brokers at bruce.wayne@expeditors.com")
            else:
                st.successs=("No ITN has duplicated SLIs with another")
        st.divider()

        st.subheader("Missing SLI in GTS-SLI")
        success, message, unmapped_sli_df = update_data_detection.find_map_sli_not_in_gts(gts_sli_df,sli_map_df)
        if not success:
            st.warning(message)
        else:
            if not unmapped_sli_df.empty:
                st.dataframe(unmapped_sli_df, use_container_width=True)
                st.warning(f"{len(unmapped_sli_df)} SLIs are not in GTS-SLI")
            else:
                st.success("All SLIs in SLI Map are in GTS-SLI")
        st.divider()

        st.subheader("Missing SLI in Export Decleration")
        success, message, not_in_dec_sli_df = update_data_detection.find_map_sli_not_in_export_dec(export_dec_df, sli_map_df)
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
        sap_download_df = update_data_detection.build_sap_download_df()
        if sap_download_df.empty:
            st.success("No ITNs currently require SAP download")
        else:
            st.dataframe(sap_download_df, use_container_width=True)
            st.warning(f"{len(sap_download_df)} AVL/SLI missing and need downloading from SAP")
        st.divider()

        st.subheader("Run Intercompany Cockpit with APL")
        build_run_intercompany_df = update_data_detection.build_run_intercompany_cockpit()
        if build_run_intercompany_df.empty:
            st.success("No ITNs currently require running Intercompany Cockpit")
        else:
            st.dataframe(build_run_intercompany_df, use_container_width=True)
            st.warning(f"{len(build_run_intercompany_df)} ITNs need running intercompany cockpit to obtain missing AVL and SLI")

if __name__ == "__main__":
    main()