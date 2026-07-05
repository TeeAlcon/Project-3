from pathlib import Path
import hashlib

import pandas as pd

# Utility
AES_FILE = Path("Updated Report") / "AES Report.csv"
GTS_FILE = Path("Updated Report") / "GTS SLI.csv"
SLI_MAP_FILE = Path("Updated Report") / "SLI Map.csv"
SEA_EXPORT_FILE = Path("Updated Report") / "Sea Export Date.csv"
DOC_SEARCH_FILE = Path("Updated Report") / "Doc Search.csv"
AUDIT_DOC_FILE = Path("Updated Report") / "Audit Doc.csv"
MASTER_LIST_FILE = Path("Updated Report") / "Master List.csv"
Path("Updated Report").mkdir(parents=True, exist_ok=True)

REQUIRED_COLS_FOR_CONFIG = {
    AES_FILE: {"ITN", "Shipment Reference Number", "Filer Name"},
    GTS_FILE: {"SLI"},
    SLI_MAP_FILE: {"ITN", "Invoice type", "Invoice number"},
    SEA_EXPORT_FILE: {"ITN", "Container Number"},
    DOC_SEARCH_FILE: {"ITN", "Total PDF count", "SLI file count", "AVL file count", "Packing-List file count", "AWB file count", "SWB file count"},
    AUDIT_DOC_FILE: {"ITN", "Value Diff", "Qty Diff"},
}

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

def find_map_sli_not_in_gts(gts_sli_df: pd.DataFrame, sli_map_df: pd.DataFrame):
    if gts_sli_df.empty or sli_map_df.empty:
        return False, "GTS SLI or SLI Map file is missing.", pd.DataFrame()

    GTS_SLI_COL = next((col for col in gts_sli_df.columns if col.lower() == "sli"), None)

    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"), None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)

    # Extract only SLI records
    sli_df = sli_map_df[sli_map_df[invoice_type_col].astype(str).str.strip().str.upper().eq("SLI")].copy()

    gts_sli_df[GTS_SLI_COL] = (gts_sli_df[GTS_SLI_COL].astype(str).str.strip())

    sli_df[invoice_number_col] = (sli_df[invoice_number_col].astype(str).str.strip())

    mapped_sli_set = (gts_sli_df[GTS_SLI_COL].replace("", pd.NA).dropna().drop_duplicates())

    unmapped_sli_df = (
        sli_df[~sli_df[invoice_number_col].isin(mapped_sli_set)][[invoice_number_col]].drop_duplicates().rename(columns={invoice_number_col: "SLI"}).reset_index(drop=True)
    )

    return True, "", unmapped_sli_df

def find_itns_with_duplicate_slis(sli_map_df: pd.DataFrame):
    if sli_map_df.empty:
        return []

    itn_col = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)

    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"),None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)

    if not itn_col or not invoice_type_col or not invoice_number_col:
        return []

    # Keep only SLI records
    df = sli_map_df[sli_map_df[invoice_type_col].astype(str).str.strip().str.upper().eq("SLI")][[itn_col, invoice_number_col]].copy()

    df[itn_col] = df[itn_col].astype(str).str.strip()
    df[invoice_number_col] = df[invoice_number_col].astype(str).str.strip()

    # Find SLIs assigned to multiple ITNs
    duplicate_slis = (df.groupby(invoice_number_col)[itn_col].nunique().loc[lambda s: s > 1].index)

    # Return affected ITNs
    duplicate_itns = (df[df[invoice_number_col].isin(duplicate_slis)][itn_col].drop_duplicates().tolist())

    return duplicate_itns, duplicate_slis

def build_master_list():
    if not AES_FILE.exists():
        return False, "AES file is missing. Do not proceed until attaining the file", pd.DataFrame()

    if not DOC_SEARCH_FILE.exists():
        return False, "Doc Search is missing. Do not proceed until attaining the file", pd.DataFrame()
   
    if not SEA_EXPORT_FILE.exists():
        return False, "Sea Export is missing. Do not proceed until attaining the file", pd.DataFrame()
   
    if not AUDIT_DOC_FILE.exists():
        return False, "Audit Doc is missing. Do not proceed until attaining the file", pd.DataFrame()

    aes_df = load_save(AES_FILE)
    doc_df = load_save(DOC_SEARCH_FILE)

    if aes_df.empty:
        return False, "AES file is empty.", pd.DataFrame()

    if doc_df.empty:
        return False, "Doc Search file is empty.", pd.DataFrame()

    ITN_COL = next((col for col in doc_df.columns if col.lower() == "itn"), None)

    if ITN_COL is None:
        return False, "ITN column not found in Doc Search.", pd.DataFrame()

    if ITN_COL not in aes_df.columns:
        return False, f"{ITN_COL} not found in AES file.", pd.DataFrame()

    # Normalize ITNs before merge
    aes_df[ITN_COL] = (aes_df[ITN_COL].astype(str).str.strip())

    doc_df[ITN_COL] = (doc_df[ITN_COL].astype(str).str.strip())

    # Merge AES with Doc Search
    master_df = aes_df.merge(doc_df, on=ITN_COL, how="left")
    save_csv(master_df.drop_duplicates(),MASTER_LIST_FILE)

    # Find ITNs with no Doc Search data
    doc_cols = [
        col
        for col in doc_df.columns
        if col != ITN_COL
    ]

    if doc_cols:
        fail_mask = (master_df[doc_cols].isna()| (master_df[doc_cols] == "")).all(axis=1)

        fail_match_df = (master_df.loc[fail_mask, [ITN_COL]].drop_duplicates().reset_index(drop=True))
    else:
        fail_match_df = pd.DataFrame(columns=[ITN_COL])

    return (True,"Master List updated with Doc Search and Audit data",fail_match_df)

def master_list_doc_ready(master_df: pd.DataFrame):
    if master_df.empty:
        return pd.DataFrame(), [], pd.DataFrame(), []

    df = master_df.copy()

    ITN_COL = "ITN"

    required_count_cols = [
        "SLI file count",
        "AVL file count",
        "APL file count",
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
        (df["Packing-List file count"] > 0) & (df["AVL file count"] > 0) & (df["APL file count"] > 0) & (df["SLI file count"] > 0) & ((df["AWB file count"] > 0) | (df["SWB file count"] > 0))
    )

    # Number of AVL, Packing-List, and SLI must match
    counts_match = (
        (df["AVL file count"] == df["Packing-List file count"]) & (df["AVL file count"] == df["SLI file count"])
    )
   
    # ITNs with duplicated SLI check
   
    duplicate_itns, duplicate_slis = find_itns_with_duplicate_slis(load_save(SLI_MAP_FILE))

    itn_with_duplicated_sli_with_other = (df[ITN_COL].astype(str).str.strip().isin(duplicate_itns))

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
    df["Document status"] = "Fail"
    df.loc[has_all_doc & counts_match & swb_check & ~itn_with_duplicated_sli_with_other, "Document status"] = "Pass"

    # Reason for Doc status = Fail
    df["Missing AVL"] = df["AVL file count"] == 0
    df["Missing Packing List"] = df["Packing-List file count"] == 0
    df["Missing SLI"] = df["SLI file count"] == 0
    df["Missing APL"] = df["APL file count"] == 0
    df["Missing AWB/SWB"] = (df["AWB file count"] == 0) & (df["SWB file count"] == 0)
    df["Number of document doesn't match"] = ~counts_match
    df["ITN with swb not in Sea Export"] = swb_exist & ~swb_valid
    df["ITN with duplicated SLI with another ITN"] = itn_with_duplicated_sli_with_other

    error_cols = [
    col for col in [
        ITN_COL,
        "Missing SLI",
        "Missing AVL",
        "Missing APL",
        "Missing Packing List",
        "Missing AWB/SWB",
        "Number of document doesn't match",
        "ITN with swb not in Sea Export",
        "ITN with duplicated SLI with another ITN"
        ]
    if col in df.columns]

    doc_not_ready_df = (
        df.loc[df["Document status"] == "Fail", error_cols].drop_duplicates().reset_index(drop=True)
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

    # Audit check
    audit_ready_df = pd.DataFrame()
    audit_ready_itns = []

    if AUDIT_DOC_FILE.exists():
        audit_df = load_save(AUDIT_DOC_FILE)
       

        if not audit_df.empty:
            audit_itn_col = next((col for col in audit_df.columns if col.lower() == "itn"), None)
            audit_value_diff_col = next((col for col in audit_df.columns if col.lower() ==  "value diff"), None) # must have a "value diff" header column to be considered for audit check
            audit_qty_diff_col =  next((col for col in audit_df.columns if col.lower() == "qty diff"), None) # must have a "qty diff" header column to be considered for audit

            if audit_itn_col and audit_value_diff_col and audit_qty_diff_col:
                for col in [audit_value_diff_col, audit_qty_diff_col]:
                    audit_df[col] = (audit_df[col].astype(str).str.replace(r"[\$,]", "", regex=True).str.strip())
           
                audit_df[audit_value_diff_col] = pd.to_numeric(audit_df[audit_value_diff_col], errors="coerce").fillna(0)
                audit_df[audit_qty_diff_col] = pd.to_numeric(audit_df[audit_qty_diff_col], errors="coerce").fillna(0)
                audit_pass = ((audit_df[audit_value_diff_col] < 100) & (audit_df[audit_qty_diff_col] < 100))

                audit_ready_df = (
                    audit_df.loc[audit_pass, [audit_itn_col, audit_value_diff_col, audit_qty_diff_col]].drop_duplicates().reset_index(drop=True)
                )

                audit_df[audit_itn_col] = (
                    audit_df[audit_itn_col]
                    .astype(str)
                    .str.strip()
                )

                audit_ready_itns = (
                    audit_ready_df[audit_itn_col]
                    .astype(str)
                    .str.strip()
                    .replace("", pd.NA)
                    .dropna()
                    .drop_duplicates()
                    .tolist()
                )

    df["Audit status"] = "Fail"
    df.loc[df[ITN_COL].astype(str).isin(audit_ready_itns), "Audit status"] = "Pass"
   
    return df, doc_not_ready_df, doc_not_ready_itns, audit_ready_df, audit_ready_itns

