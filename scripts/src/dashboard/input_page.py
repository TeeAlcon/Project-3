import pandas as pd
import streamlit as st
from utils.file_utils import (clean_columns, load_save, save_csv, read_csv)
import utils.file_analyzed

from config import REPORTS, HIERARCHIAL_REPORT, ALL_REPORTS
from datetime import datetime


def render_input_viewer(title: str, input_df: pd.DataFrame) -> None:
        if input_df.empty:
            st.info(f"{title} is missing or empty.")
            return

        filter_columns = st.multiselect(
            "Filter columns",
            options=input_df.columns.tolist(),
            key=f"filter_columns_{title}",
        )

        filtered_df = input_df.copy()

        for column in filter_columns:
            filter_text = st.text_input(
                column,
                key=f"filter_value_{title}_{column}",
                placeholder=f"Search {column}",
            )

            if filter_text:
                filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(filter_text, case=False, na=False, regex=False)]

        st.caption(f"Showing {len(filtered_df):,} of {len(input_df):,} rows")

        if filtered_df.empty:
            st.info("No matching rows found.")
            return

        height = "content" if len(filtered_df) < 14 else 600

        st.dataframe(filtered_df, hide_index=True, use_container_width=True, height=height)


def render():
    st.title("Data Import")

    status = []


    for report in ALL_REPORTS.values():
        path = report["path"]

        df = load_save(path)

        if path.exists():
            date_uploaded = datetime.fromtimestamp(path.stat().st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            date_modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")        
        else: 
            date_uploaded = ""
            date_modified = ""

        status.append({
            "Report": report["title"],
            "Loaded": "Yes" if path.exists() else "No",
            "Date Uploaded": date_uploaded,
            "Date Modified": date_modified
        })

    st.subheader("Current Status")
    st.dataframe(
        pd.DataFrame(status),
        use_container_width=True
    )

    report_key = st.selectbox(
        "Select report",
        list(ALL_REPORTS.keys()),
        format_func=lambda x: ALL_REPORTS[x]["title"],
    )

    if "current_report" not in st.session_state:
        st.session_state.current_report = report_key
    elif st.session_state.current_report != report_key:
        for report in ALL_REPORTS.values():
            st.session_state.pop(report["title"] + "_data", None)
        st.session_state.current_report =  report_key

    report = ALL_REPORTS[report_key]

    st.divider()

    input_page(report["title"], report["path"], report["id_col"], report_key in HIERARCHIAL_REPORT)


def input_page(title, base_file, id_col, is_hierarchical=False):
    st.title(title)
    save_df = load_save(base_file)
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"],key=title)

    if uploaded_file:
         
        import_df = (clean_columns(read_csv(uploaded_file)))

        valid, message = (utils.file_analyzed.validate_report_structure(import_df,base_file))

        if not valid:
            st.error(message)
            st.stop()

        if id_col in import_df.columns:
            import_df[id_col] = (import_df[id_col].astype(str).str.strip().str.replace(r"\s+","",regex=True))

        if (save_df.empty and not base_file.exists()):
            save_csv(
                import_df,
                base_file
            )
            st.success("Initial file saved.")
            st.rerun()

        if st.button("Analyze report", type="primary",key=title + "_analyze"):
            try:
                if is_hierarchical:
                    updated_df, rows_added = (utils.file_analyzed.analyze_hierarchical_import(save_df,import_df, id_col))
                    st.session_state[title + "_data"] = (updated_df, rows_added)
                else: 
                    updated_df, rows_added = (utils.file_analyzed.analyze_import(save_df,import_df, id_col))
                    st.session_state[title + "_data"] = (updated_df, rows_added)
            except ValueError as e:
                st.error(str(e))

    if title + "_data" in st.session_state:

        updated_df, rows_added = (st.session_state[title + "_data"])

        tab1, tab2 = st.tabs(["Rows added","Final save preview"])

        with tab1: st.dataframe(rows_added, use_container_width=True)

        with tab2: st.dataframe(updated_df, use_container_width=True)

        if rows_added.empty:
            st.info("No change found")

        if st.button(f"Save update to {title}", type="primary",key=title + "_save"):
            save_csv(updated_df, base_file)
            st.success("Save updated")

    if base_file.exists():

        st.subheader("Current saved preview")

        current_df = (load_save(base_file))

        render_input_viewer(title, current_df)

        if st.button("Reset", key=title + "_reset"):
            base_file.unlink(missing_ok=True)
            st.session_state.pop(title + "_data", None)
            st.session_state.pop(title, None)

            st.rerun()