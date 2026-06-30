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
    build_master_list,
    master_list_doc_ready,
    find_unmapped_sli,
)

def other_run_page(title, base_file):
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

def aes_run_page(title, base_file):
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
        </style>
        """,
        unsafe_allow_html=True,
    )

    AES_PAGE_FILES = {
        "aes": ("AES Report Update", AES_FILE)
    }

    OTHER_PAGE_FILES = {
        "gts": ("GTS-SLI Update", GTS_FILE),
        "sli_map": ("SLI Map Update", SLI_MAP_FILE),
        "sea_export": ("Sea Export Update", SEA_EXPORT_FILE),
        "doc_search": ("Doc Search Update", DOC_SEARCH_FILE),
        "audit_doc": ("Audit Doc Update", AUDIT_DOC_FILE),
    }

    MASTER_PAGE = {
        "master": ("Master List Update", MASTER_LIST_FILE)
    }

    if "page" not in st.session_state:
        st.session_state.page = "aes"

    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

    with col1:
        if st.button("AES Report Update"):
            st.session_state.page = "aes"

    with col2:
        if st.button("GTS-SLI"):
            st.session_state.page = "gts"

    with col3:
        if st.button("SLI Map"):
            st.session_state.page = "sli_map"

    with col4:
        if st.button("Sea Export"):
            st.session_state.page = "sea_export"

    with col5:
        if st.button("Doc Search"):
            st.session_state.page = "doc_search"

    with col6:
        if st.button("Audit Doc"):
            st.session_state.page = "audit_doc"

    with col7:
        if st.button("Master"):
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

    if page_key in AES_PAGE_FILES:
        title, base_file = AES_PAGE_FILES[page_key]
        aes_run_page(title, base_file)

    elif page_key in OTHER_PAGE_FILES:
        title, base_file = OTHER_PAGE_FILES[page_key]
        other_run_page(title, base_file)

    elif page_key in MASTER_PAGE:
        title, base_file = MASTER_PAGE[page_key]
        st.title(title)

        master_df = load_save(base_file)

        if master_df.empty:
            st.info("Master List is empty.")
        else:
            df, doc_not_ready_df, doc_not_ready_itns = master_list_doc_ready(master_df)
            summary_df = (df[["ITN", "Doc ready status", "Audit ready status"]].drop_duplicates())
            gts_sli_df = load_save(GTS_FILE)
            sli_map_df = load_save(SLI_MAP_FILE)
            success, message, unmapped_sli_df = (find_unmapped_sli(gts_sli_df,sli_map_df))

            st.subheader("ITN Readiness Summary")
            st.dataframe(summary_df, use_container_width=True)

            st.subheader("Doc not ready ITNs")
            st.dataframe(doc_not_ready_df, use_container_width=True)
            if doc_not_ready_itns:
                st.warning(f"{len(doc_not_ready_itns)} ITNs are not ready")
            else:
                st.success("All ITNs are ready.")

            st.subheader("ITN without data in Doc Search")
            fail_match_df = st.session_state.get("fail_match_df", pd.DataFrame(columns=["ITN"]))
            if not fail_match_df.empty:
                st.dataframe(fail_match_df,use_container_width=True)
                st.warning(f"{len(fail_match_df)} ITNs do not have data in Doc Search")
            else:
                st.success("All ITNs have data in Doc Search")

            st.subheader("Unmapped SLI in GTS-SLI")
            if not success:
                st.warning(message)
            else:
                st.dataframe(unmapped_sli_df, use_container_width=True)

                if not unmapped_sli_df.empty:
                    st.warning(f"{len(unmapped_sli_df)} SLIs in GTS-SLI are not mapped in SLI Map")
                else:
                    st.success("All SLIs in GTS-SLI are mapped in SLI Map")

if __name__ == "__main__":
    main()
