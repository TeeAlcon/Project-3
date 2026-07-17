import pandas as pd
import streamlit as st

import utils.update_data_detection as update_data_detection

from config import REPORTS
from datetime import datetime


def render():
    st.title("Data Import")

    status = []

    for report in REPORTS.values():
        path = report["path"]

        df = update_data_detection.load_save(path)

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
        list(REPORTS.keys()),
        format_func=lambda x: REPORTS[x]["title"],
    )

    report = REPORTS[report_key]

    st.divider()

    document_page(
        report["title"],
        report["path"],
        report["id_col"]
    )


def document_page(title, base_file, id_col):
    st.title(title)

    save_df = update_data_detection.load_save(base_file)

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"],key=title)

    if uploaded_file:
        import_df = (update_data_detection.clean_columns(update_data_detection.read_csv(uploaded_file)))

        valid, message = (update_data_detection.validate_report_structure(import_df,base_file))

        if not valid:
            st.error(message)
            st.stop()

        if id_col in import_df.columns:
            import_df[id_col] = (import_df[id_col].astype(str).str.strip().str.replace(r"\s+","",regex=True))

        if (save_df.empty and not base_file.exists()):
            update_data_detection.save_csv(
                import_df,
                base_file
            )
            st.success("Initial file saved.")
            st.rerun()

        if st.button("Analyze report", type="primary",key=title + "_analyze"):
            try:
                updated_df, rows_added = (update_data_detection.analyze_import(save_df,import_df, id_col))
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
            update_data_detection.save_csv(updated_df, base_file)
            st.success("Save updated")

    if base_file.exists():

        st.subheader("Current saved preview")

        st.dataframe(update_data_detection.load_save(base_file),
            height=500,
            use_container_width=True
        )

        if st.button("Reset", key=title + "_reset"):
            base_file.unlink(missing_ok=True)
            st.session_state.pop(title + "_data", None)
            st.session_state.pop(title, None)

            st.rerun()