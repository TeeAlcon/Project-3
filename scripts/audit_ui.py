import pandas as pd
import streamlit as st

from update_data_detection import (
    AES_FILE,
    GTS_FILE,
    SLI_MAP_FILE,
    SEA_EXPORT_FILE,
    DOC_SEARCH_FILE,
    AUDIT_DOC_FILE,
    MASTER_LIST_FILE,
    read_csv,
    clean_columns,
    load_save,
    save_csv,
    analyze_import,
    find_map_sli_not_in_gts,
    build_master_list,
    master_list_doc_ready,
)

def document_page(title, base_file):
    st.title(title)

    save_df = load_save(base_file)
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"], key=title)

    if uploaded_file:
        import_df = clean_columns(read_csv(uploaded_file))
        id_col = st.selectbox("ID column", import_df.columns, key=title + "_selectbox")
        st.session_state[title + "_id_col"] = id_col

        if save_df.empty and not base_file.exists():
            save_csv(import_df, base_file)
            st.success("Initial file saved.")
            st.rerun()

        if st.button("Analyze report", type="primary", key=title + "_analyze"):
            try:
                updated_df, rows_added = analyze_import(save_df, import_df, id_col)
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
            save_csv(updated_df, base_file)
            st.success("Save updated")

    if base_file.exists():
        st.subheader("Current saved preview")
        st.dataframe(load_save(base_file), height=500, use_container_width=True)

        if st.button("Reset", key=title + "_reset"):
            base_file.unlink(missing_ok=True)

            # Clear only this page's session data instead of everything
            st.session_state.pop(title + "_data", None)
            st.session_state.pop(title + "_id_col", None)

            st.rerun()

def data_page():
    st.title("Data Import")

    IMPORT_FILES = {
        "aes": ("AES Report", AES_FILE),
        "gts": ("GTS-SLI", GTS_FILE),
        "sli_map": ("SLI Map", SLI_MAP_FILE),
        "sea_export": ("Sea Export", SEA_EXPORT_FILE),
        "doc_search": ("Doc Search", DOC_SEARCH_FILE),
        "audit_doc": ("Audit Doc", AUDIT_DOC_FILE),
    }

    status = []

    for key, (label, path) in IMPORT_FILES.items():
        df = load_save(path)

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

# UI. Start here
def main():
    st.set_page_config(page_title="REPORT UPDATE", layout="wide")

    # Optional: hide Streamlit UI
    st.markdown(
        """
        <style>
          #MainMenu {visibility: hidden;}
          footer {visibility: hidden;}
          .stDeployButton {display:none;}
          .stAppDeployButton {display:none;}

        div.stButton > button {
          width: 100%;
          border: 1px solid color-mix(in srgb, currentColor 30%, transparent);
          background-color:
            color-mix(
               in srgb,
               var(--background-color) 92%,
               currentColor 8%
            );
          color:var (--text-color);
          font-weight: 600;
          border-radius: 8px;
          padding: 0.5rem 0.75rem;
        }

        div.stButton > button:hover {
          border-color: var(--primary-color);
          background-color:
            color-mix(
               in srgb,
               var(--primary-color) 12%.
               var(--background-color)
            );
          color: var(--text-color);
        }

        div.stButton > button:focus {
          border-color: var(--primary-color);
          box-shadow: 0 0 0 2px
            color-mix(
                in srgb,
                var(--primary-color) 25%,
                transparent
            );
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    MASTER_PAGE = {
        "master": ("Master List", MASTER_LIST_FILE)
    }

    if "page" not in st.session_state:
        st.session_state.page = "data"

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Data", use_container_width = True):
            st.session_state.page = "data"

    with col2:
        if st.button("Master", use_container_width = True):
            success, message, fail_match_df = build_master_list()

            st.session_state["master_success"] = success
            st.session_state["master_message"] = message
            st.session_state["fail_match_df"] = fail_match_df

            st.session_state.page = "master"
            st.rerun()

    st.divider()

    if "master_message" in st.session_state:
        msg = st.session_state.pop("master_message")
        success = st.session_state.pop("master_success", True)

        if success:
            st.success(msg)
        else:
            st.error(msg)

    page_key = st.session_state.page

    if page_key == "data":
        data_page()

    elif page_key in MASTER_PAGE:
        title, base_file = MASTER_PAGE[page_key]
        st.title(title)

        master_df = load_save(base_file)

        if master_df.empty:
            st.info("Master List is empty.")
        else:
            gts_sli_df = load_save(GTS_FILE)
            sli_map_df = load_save(SLI_MAP_FILE)
            df, doc_not_ready_df, doc_not_ready_itns, audit_ready_df, audit_ready_itns = master_list_doc_ready(master_df)
            summary_df = (df[["ITN", "Document status", "Audit status"]].drop_duplicates())
            success, message, unmapped_sli_df = (find_map_sli_not_in_gts(gts_sli_df,sli_map_df))

            st.subheader("ITN Readiness Summary")
            st.dataframe(summary_df, use_container_width=True)

            st.subheader("ITNs failling document audit")
            st.dataframe(doc_not_ready_df, use_container_width=True)
            if doc_not_ready_itns:
                st.warning(f"{len(doc_not_ready_itns)} ITNs with missing documents")
            else:
                st.success("All ITNs are ready.")

            st.subheader("Missing SLI in GTS-SLI")
            if not success:
                st.warning(message)
            else:
                if not unmapped_sli_df.empty:
                    st.dataframe(unmapped_sli_df, use_container_width=True)
                    st.warning(f"{len(unmapped_sli_df)} SLIs are not in GTS-SLI")
                else:
                    st.success("All SLIs in SLI Map are in GTS-SLI")

if __name__ == "__main__":
    main()
