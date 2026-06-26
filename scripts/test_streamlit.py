from pathlib import Path
import hashlib

import pandas as pd
import streamlit as st

# Utility
AES_FILE = Path("Updated Report") / "ACE Report Update.csv"
GTS_FILE = Path("Updated Report") / "GTS SLI.csv"
SLI_MAP_FILE = Path("Updated Report") / "SLI map.csv"
SEA_EXPORT_FILE = Path("Updated Report") / "Sea Export Date.csv"
DOC_SEARCH_FILE = Path("Updated Report") / "Doc Search.csv"
AUDIT_DOC_FILE = Path("Updated Report") / "Audit Doc.csv"
MASTER_LIST_FILE = Path("Updated Report") / "Master List.csv"
Path("Updated Report").mkdir(parents=True, exist_ok=True)

# Turn CSV to pandas DataFrame + turn columns to text
def read_csv(file_or_path) -> pd.DataFrame:
    try: return pd.read_csv(file_or_path, dtype=str, keep_default_na=False).fillna("")
    except UnicodeDecodeError:
        return pd.read_csv(
            file_or_path,
            dtype=str,
            keep_default_na=False,
            encoding="cp1252"   # or "latin1"
        ).fillna("")

# Clean column header
def clean_columns(df):
    df.columns = df.columns.str.strip().str.replace("\xa0", " ", regex=False)
    return df

def save_csv(df: pd.DataFrame, path: Path):
    df.to_csv(path, index=False, encoding="utf-8-sig")

def load_save(base_file):
    return read_csv(base_file) if base_file.exists() else pd.DataFrame()

def normalize_columns(save_df: pd.DataFrame, import_df: pd.DataFrame):
    all_cols = list(dict.fromkeys(list(save_df.columns) + list(import_df.columns)))
    for col in all_cols:
        if col not in save_df.columns:
            save_df[col] = ""
        if col not in import_df.columns:
            import_df[col] = ""
    return save_df[all_cols].fillna(""), import_df[all_cols].fillna("")

# Stable fingerprint for all rows in one ID group.
def canonical_group_hash(df: pd.DataFrame, compare_cols: list[str]) -> str:
    if df.empty:
        payload = ""
    else:
        payload = df[compare_cols].astype(str).fillna("").to_csv(
            index=False,
            lineterminator="\n")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

# Detect changes. Return updated_df, rows_added
def analyze_import(save_df: pd.DataFrame, import_df: pd.DataFrame, id_col: str):
    if id_col not in import_df.columns:
        raise ValueError(f"Upload missing ID column: {id_col}")

    if len(save_df) and id_col not in save_df.columns:
        raise ValueError(f"Save missing ID column: {id_col}")

    import_df = import_df.copy()
    save_df = save_df.copy()

    # Normalize ID column
    import_df[id_col] = import_df[id_col].astype(str).str.strip()
    if len(save_df):
        save_df[id_col] = save_df[id_col].astype(str).str.strip()

    if (import_df[id_col] == "").any():
        raise ValueError("Upload contains blank IDs.")

    if save_df.empty:
        save_df = pd.DataFrame(columns=import_df.columns)

    save_df, import_df = normalize_columns(save_df, import_df)
    compare_cols = list(save_df.columns)

    # Consistent ordering before hashing
    save_df = save_df.sort_values(compare_cols).reset_index(drop=True)
    import_df = import_df.sort_values(compare_cols).reset_index(drop=True)

    # row-level hashing
    save_df["_row_hash"] = pd.util.hash_pandas_object(
        save_df[compare_cols],
        index=False
    )
    import_df["_row_hash"] = pd.util.hash_pandas_object(
        import_df[compare_cols],
        index=False
    )

    old_hashes = (
        save_df.groupby(id_col)["_row_hash"]
        .apply(lambda x: hashlib.sha256(x.values.tobytes()).hexdigest())
        .to_dict()
    )

    new_hashes = (
        import_df.groupby(id_col)["_row_hash"]
        .apply(lambda x: hashlib.sha256(x.values.tobytes()).hexdigest())
        .to_dict()
    )

    # Detect changed or new IDs
    replace_ids = [
        val for val in new_hashes
        if old_hashes.get(val) != new_hashes[val]
    ]

    # Build result datasets
    rows_added = import_df[import_df[id_col].isin(replace_ids)]
    kept = save_df[~save_df[id_col].isin(replace_ids)]

    updated_df = pd.concat([kept, rows_added], ignore_index=True)

    # Clean up helper column
    updated_df = updated_df.drop(columns=["_row_hash"], errors="ignore")
    rows_added = rows_added.drop(columns=["_row_hash"], errors="ignore")

    return updated_df, rows_added

def export_id_col(save_df: pd.DataFrame, id_col: str):
    if save_df.empty or not id_col:
        return False

    if id_col not in save_df.columns:
        return False

    master_path = MASTER_LIST_FILE

    # Prepare ID column
    new_col_df = (save_df[id_col].astype(str).str.strip().replace("", pd.NA).dropna().drop_duplicates().reset_index(drop=True).to_frame(name=id_col))

    # If file exists then append/replace column
    if master_path.exists():
        existing_df = read_csv(master_path)

        # Align row counts
        max_len = max(len(existing_df), len(new_col_df))
        existing_df = existing_df.reindex(range(max_len))
        new_col_df = new_col_df.reindex(range(max_len))

        # Replace existing column if it exists
        if id_col in existing_df.columns:
            existing_df = existing_df.drop(columns=[id_col])

        master_df = pd.concat([existing_df, new_col_df], axis=1)

    else:
        master_df = new_col_df

    save_csv(master_df, master_path)
    return True

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

# Mapping ITN to data in Doc Search
def itn_doc_mapping():
    if not AES_FILE.exists() or not DOC_SEARCH_FILE.exists():
        return False, "AES or Doc Search file is missing.", pd.DataFrame()

    aes_df = load_save(AES_FILE)
    doc_df = load_save(DOC_SEARCH_FILE)

    ITN_COL = next(col for col in doc_df.columns if col.lower() == "itn")

    if ITN_COL not in aes_df.columns:
        return False, f"{ITN_COL} not found in AES file.", pd.DataFrame()

    aes_df[ITN_COL] = aes_df[ITN_COL].astype(str).str.strip()
    doc_df[ITN_COL] = doc_df[ITN_COL].astype(str).str.strip()

    merged_df = aes_df.merge(
        doc_df,
        on=ITN_COL,
        how="left"
    )

    doc_cols = doc_df.columns.tolist()[1:]
    doc_cols = [col for col in doc_cols if col in merged_df.columns]

    if doc_cols:
        fail_mask = merged_df[doc_cols].isna() | (merged_df[doc_cols] == "")
        fail_mask = fail_mask.all(axis=1)

        fail_match_df = (merged_df.loc[fail_mask, [ITN_COL]].drop_duplicates().reset_index(drop=True))
    else:
        # If Doc Search has no extra columns
        fail_match_df = (merged_df[[ITN_COL]].drop_duplicates().reset_index(drop=True))

    # Save final output
    save_csv(merged_df.drop_duplicates(), MASTER_LIST_FILE)

    return True, "Master List updated with Doc Search data.", fail_match_df


def update_master_from_current_page(page_key):
    ALL_PAGE_FILES = {
        "aes": ("AES Report Update", AES_FILE),
        "gts": ("GTS-SLI Update", GTS_FILE),
        "sli_map": ("SLI Map Update", SLI_MAP_FILE),
        "sea_export": ("Sea Export Update", SEA_EXPORT_FILE),
        "doc_search": ("Doc Search Update", DOC_SEARCH_FILE),
        "audit_doc": ("Audit Doc Update", AUDIT_DOC_FILE),
    }

    if page_key not in ALL_PAGE_FILES:
        st.session_state["master_message"] = "No report page selected."
        st.session_state["master_message_type"] = "warning"
        return

    title, base_file = ALL_PAGE_FILES[page_key]

    # Load current page data
    if title + "_data" in st.session_state:
        updated_df, _ = st.session_state[title + "_data"]
    else:
        updated_df = load_save(base_file)

    if updated_df.empty:
        st.session_state["master_message"] = "No data found."
        st.session_state["master_message_type"] = "warning"
        return

    # Load Doc Search
    if not DOC_SEARCH_FILE.exists():
        st.session_state["master_message"] = "Doc Search file is missing."
        st.session_state["master_message_type"] = "error"
        return

    doc_df = load_save(DOC_SEARCH_FILE)
    ITN_COL = next((col for col in doc_df.columns if col.lower() == "itn"), None)

    if ITN_COL not in updated_df.columns:
        st.session_state["master_message"] = f"{ITN_COL} not found in current data."
        st.session_state["master_message_type"] = "error"
        return

    # Clean ITN
    updated_df[ITN_COL] = updated_df[ITN_COL].astype(str).str.strip()
    doc_df[ITN_COL] = doc_df[ITN_COL].astype(str).str.strip()

    # Merge
    master_df = updated_df.merge(
        doc_df,
        on=ITN_COL,
        how="left"
    )

    save_csv(master_df, MASTER_LIST_FILE)

    # Identify unmatched ITNs
    doc_cols = doc_df.columns.tolist()[1:]
    doc_cols = [col for col in doc_cols if col in master_df.columns]

    if doc_cols:
       fail_mask = master_df[doc_cols].isna() | (master_df[doc_cols] == "")
       fail_mask = fail_mask.all(axis=1)
       fail_match_df = (master_df.loc[fail_mask, [ITN_COL]].drop_duplicates().reset_index(drop=True))
    else:
        fail_match_df = master_df[[ITN_COL]].drop_duplicates().reset_index(drop=True)

    st.session_state["master_message"] = "Master List updated from Doc Search."
    st.session_state["master_message_type"] = "success"
    st.session_state["fail_match_df"] = fail_match_df

def master_list_doc_ready(master_df: pd.DataFrame):
    if master_df.empty:
        return pd.DataFrame(), [], pd.DataFrame(), []

    df = master_df.copy()

    ITN_COL = "ITN"

    required_count_cols = [
        "SLI file count",
        "AVL file count",
        "Packing-List file count",
        "AWB file count",
        "SWB file count",
    ]

    # Make sure all required columns exist
    for col in required_count_cols:
        if col not in df.columns:
            df[col] = 0

    # Convert count columns to numbers
    for col in required_count_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # ITN must have at least one Packing-List, AVL, SLI, AWB, or SWB
    has_all_doc = (
        (df["Packing-List file count"] > 0) & (df["AVL file count"] > 0) & (df["SLI file count"] > 0) & ((df["AWB file count"] > 0) | (df["SWB file count"] > 0))
    )

    # Number of AVL, Packing-List, and SLI must match
    counts_match = (
        (df["AVL file count"] == df["Packing-List file count"]) & (df["AVL file count"] == df["SLI file count"])
    )

    # ITN have swb must be in Sea Export
    swb_exist = df["SWB file count"] > 0
    if SEA_EXPORT_FILE.exists():
        sea_df = load_save(SEA_EXPORT_FILE)
        if not sea_df.empty:
            sea_itn_col = next((col for col in sea_df.columns if col.lower() == "itn"), None)
            sea_itn_set = (sea_df[sea_itn_col].astype(str).str.strip().replace("", pd.NA).dropna().drop_duplicates())
            swb_valid = df[ITN_COL].astype(str).isin(sea_itn_set)
        else:
            swb_valid = False
    else:
        swb_valid = False
    swb_check = (~swb_exist) | (swb_exist & swb_valid)

    # Final ready/not_ready result
    df["Doc ready status"] = "not_ready"
    df.loc[has_all_doc & counts_match & swb_check, "Doc ready status"] = "ready"

    # Reason for Doc ready status = not_ready
    df["Missing AVL"] = df["AVL file count"] == 0
    df["Missing Packing List"] = df["Packing-List file count"] == 0
    df["Missing SLI"] = df["SLI file count"] == 0
    df["Missing AWB/SWB"] = (df["AWB file count"] == 0) & (df["SWB file count"] == 0)
    df["Number of document doesn't match"] = ~counts_match
    df["ITN with swb not in Sea Export"] = swb_exist & ~swb_valid
   

    error_cols = [
    col for col in [
        ITN_COL,
        "Missing SLI",
        "Missing AVL",
        "Missing Packing List",
        "Missing AWB/SWB",
        "Number of document doesn't match",
        "ITN with swb not in Sea Export"
        ]
    if col in df.columns]

    doc_not_ready_df = (
        df.loc[df["Doc ready status"] == "not_ready", error_cols].drop_duplicates().reset_index(drop=True)
    )

    doc_not_ready_itns = (
        doc_not_ready_df[ITN_COL]
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .tolist()
    )

   
    # Audit check (change the logic/ default)
    audit_not_ready_df = pd.DataFrame()
    audit_not_ready_itns = []

    if AUDIT_DOC_FILE.exists():
        audit_df = load_save(AUDIT_DOC_FILE)
       

        if not audit_df.empty:
            audit_itn_col = next((col for col in audit_df.columns if col.lower() == "itn"), None)
            audit_value_diff_col = next((col for col in audit_df.columns if col.lower() ==  "value diff"), None)
            audit_qty_diff_col =  next((col for col in audit_df.columns if col.lower() == "qty diff"), None)

            if audit_itn_col and audit_value_diff_col and audit_qty_diff_col:
                for col in [audit_value_diff_col, audit_qty_diff_col]:
                    audit_df[col] = (audit_df[col].astype(str).str.replace(r"[\$,]", "", regex=True).str.strip())
           
                audit_df[audit_value_diff_col] = pd.to_numeric(audit_df[audit_value_diff_col], errors="coerce").fillna(0)
                audit_df[audit_qty_diff_col] = pd.to_numeric(audit_df[audit_qty_diff_col], errors="coerce").fillna(0)
                audit_fail = ((audit_df[audit_value_diff_col] >= 100) | (audit_df[audit_qty_diff_col] >= 100))

                audit_not_ready_df = (
                    audit_df.loc[audit_fail, [audit_itn_col, audit_value_diff_col, audit_qty_diff_col]].drop_duplicates().reset_index(drop=True)
                )

                audit_df[audit_itn_col] = (
                    audit_df[audit_itn_col]
                    .astype(str)
                    .str.strip()
                )

                audit_not_ready_itns = (
                    audit_not_ready_df[audit_itn_col]
                    .astype(str)
                    .str.strip()
                    .replace("", pd.NA)
                    .dropna()
                    .drop_duplicates()
                    .tolist()
                )

    df["Audit ready status"] = "ready"
    df.loc[df[ITN_COL].astype(str).isin(audit_not_ready_itns), "Audit ready status"] = "not_ready"
   
    return df, doc_not_ready_df, doc_not_ready_itns

def find_unmapped_sli(gts_sli_df: pd.DataFrame, sli_map_df: pd.DataFrame):
    SLI_COL = next((col for col in sli_map_df.columns if col.lower() == "sli"),None)
    SLI_COL = next((col for col in gts_sli_df.columns if col.lower() == "sli"), None)
    gts_sli_df[SLI_COL] = gts_sli_df[SLI_COL].astype(str).str.strip()
    sli_map_df[SLI_COL] = sli_map_df[SLI_COL].astype(str).str.strip()

    # Build lookup set from SLI Map
    mapped_sli_set = (
        sli_map_df[SLI_COL].replace("", pd.NA).dropna().drop_duplicates()
    )

    # Identify unmapped SLIs
    unmapped_sli_df = (
        gts_sli_df[~gts_sli_df[SLI_COL].isin(mapped_sli_set)][[SLI_COL]].drop_duplicates().reset_index(drop=True)
    )

    return unmapped_sli_df

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
   
    # ready to run new func on these pages
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
            current_page = st.session_state.get("page", "aes")

            update_master_from_current_page(current_page)

            success, msg, fail_match_df = itn_doc_mapping()

            st.session_state["master_message"] = msg
            st.session_state["master_message_type"] = "success" if success else "error"
            st.session_state["fail_match_df"] = fail_match_df

            st.session_state.page = "master"
            st.rerun()

    st.divider()

    # Show Master update message after rerun
    if "master_message" in st.session_state:
        message = st.session_state.pop("master_message")
        message_type = st.session_state.pop("master_message_type", "info")

        if message_type == "success":
            st.success(message)
        elif message_type == "warning":
            st.warning(message)
        elif message_type == "error":
            st.error(message)
        else:
            st.info(message)

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
            summary_df = df[["ITN", "Doc ready status", "Audit ready status"]].drop_duplicates()  
            gts_sli_df = load_save(GTS_FILE)
            sli_map_df = load_save(SLI_MAP_FILE)
            unmapped_sli_df = find_unmapped_sli(gts_sli_df, sli_map_df)

            st.subheader("ITN Readiness Summary")
            st.dataframe(summary_df, use_container_width = True)

            st.subheader("Doc not ready ITNs")
            st.dataframe(doc_not_ready_df, use_container_width=True)
            if doc_not_ready_itns:
                st.warning(f"{len(doc_not_ready_itns)} ITNs are not ready")
            else:
                st.success("All ITNs are ready.")

            st.subheader("ITN without data in Doc Search")
            fail_match_df = st.session_state.get("fail_match_df")
            if fail_match_df is not None and not fail_match_df.empty:
                st.dataframe(fail_match_df, use_container_width = True)
                st.warning (f"{len(fail_match_df)} ITNs do not have data in Doc Search")
            else:
                st.success("All ITNs have data in Doc Search")

            st.subheader("Unmapped SLI in GTS-SLI")
            st.dataframe(unmapped_sli_df, use_container_width=True)
            if not unmapped_sli_df.empty:
                st.warning(f"{len(unmapped_sli_df)} SLIs in GTS-SLI are not mapped in SLI Map")
            else:
                st.success("All SLIs in GTS-SLI are mapped to an ITN in SLI Map")


if __name__ == "__main__":
    main()
