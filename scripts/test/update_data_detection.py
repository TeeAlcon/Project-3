from pathlib import Path
import hashlib

import pandas as pd

# Utility
AES_FILE = Path("Drawback Report") / "AES Report.csv"
GTS_FILE = Path("Drawback Report") / "GTS SLI.csv"
SLI_MAP_FILE = Path("Drawback Report") / "SLI Map.csv"
SEA_EXPORT_FILE = Path("Drawback Report") / "Sea Export Date.csv"
DOC_SEARCH_FILE = Path("Drawback Report") / "Doc Search.csv"
AUDIT_DOC_FILE = Path("Drawback Report") / "Audit Doc.csv"
MASTER_LIST_FILE = Path("Drawback Report") / "Master List.csv"
EXPORT_DEC_FILE = Path("Drawback Report") / "Export Dec.csv"
Path("Drawback Report").mkdir(parents=True, exist_ok=True)

REQUIRED_COLS_FOR_CONFIG = {
    AES_FILE: {"ITN", "Shipment Reference Number", "Commodity Line Value", "Quantity 1"},
    GTS_FILE: {"Shipper's ref num", "Item - Value (USD)","Item - Quantity Schedule B Unit(s)"},
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

# file uploaded must have certain headers to be considered for a report
def validate_report_structure(df, base_file):
    required_cols = REQUIRED_COLS_FOR_CONFIG.get(base_file, set())

    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        return False, (
            f"Missing required columns. Please ensure you are uploading the file with correct configuration"
        )

    return True, ""

def find_map_sli_not_in_gts(gts_sli_df: pd.DataFrame, sli_map_df: pd.DataFrame):
    if gts_sli_df.empty or sli_map_df.empty:
        return False, "GTS SLI or SLI Map file is missing.", pd.DataFrame()
    
    gts_sli_df = gts_sli_df.rename(columns={"Shipper's ref num": "SLI"})
    GTS_SLI_COL = next((col for col in gts_sli_df.columns if col.lower() == "sli"), None)
    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"), None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)
    CORRESPONDING_ITN_COL = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)

    # Extract only SLI records from Invoice Number in Map SLI    
    sli_df = sli_map_df[sli_map_df[invoice_type_col].astype(str).str.strip().str.upper().eq("SLI")].copy()
    gts_sli_df[GTS_SLI_COL] = (gts_sli_df[GTS_SLI_COL].astype(str).str.strip())

    sli_df[invoice_number_col] = (sli_df[invoice_number_col].astype(str).str.strip())

    mapped_sli_set = (gts_sli_df[GTS_SLI_COL].replace("", pd.NA).dropna().drop_duplicates())

    unmapped_sli_df = (
        sli_df[~sli_df[invoice_number_col].isin(mapped_sli_set)][[CORRESPONDING_ITN_COL, invoice_number_col]].drop_duplicates().rename(columns={CORRESPONDING_ITN_COL: "ITN", invoice_number_col: "SLI"}).reset_index(drop=True)
    )

    return True, "", unmapped_sli_df

# Assign SLI in map to SLI in Export Dec
def find_map_sli_not_in_export_dec(export_dec_df: pd.DataFrame, sli_map_df: pd.DataFrame):
    if export_dec_df.empty or sli_map_df.empty:
        return False, "Export Dec or SLI Map file is missing.", pd.DataFrame()

    EXPORT_DEC_SLI_COL = export_dec_df.columns[0] # Only for Export Decleration, the first column will always be SLI col

    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"), None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)
    CORRESPONDING_ITN_COL = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)

    sli_df = sli_map_df[sli_map_df[invoice_type_col].astype(str).str.strip().str.upper().eq("SLI")].copy()
    export_dec_df[EXPORT_DEC_SLI_COL] = (export_dec_df[EXPORT_DEC_SLI_COL].astype(str).str.strip())

    sli_df[invoice_number_col] = (sli_df[invoice_number_col].astype(str).str.strip())

    in_dec_sli_set = (export_dec_df[EXPORT_DEC_SLI_COL].replace("", pd.NA).dropna().drop_duplicates())

    not_in_dec_sli_df = (
        sli_df[~sli_df[invoice_number_col].isin(in_dec_sli_set)][[CORRESPONDING_ITN_COL, invoice_number_col]].drop_duplicates().rename(columns={CORRESPONDING_ITN_COL: "ITN", invoice_number_col: "SLI"}).reset_index(drop=True)
    )

    return True, "", not_in_dec_sli_df

def find_itns_with_duplicate_slis(sli_map_df: pd.DataFrame):
    if sli_map_df.empty:
        return False, "SLI Map file is missing.", pd.DataFrame()

    itn_col = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)
    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"),None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)

    # Keep only SLI records
    df = sli_map_df[sli_map_df[invoice_type_col].astype(str).str.strip().str.upper().eq("SLI")][[itn_col, invoice_number_col]].copy()

    df[itn_col] = df[itn_col].astype(str).str.strip()
    df[invoice_number_col] = df[invoice_number_col].astype(str).str.strip()

    # Find SLIs assigned to multiple ITNs
    duplicate_slis = (df.groupby(invoice_number_col)[itn_col].nunique().loc[lambda s: s > 1].index)

    # Return affected ITNs
    duplicate_itns = (df[df[invoice_number_col].isin(duplicate_slis)][itn_col].drop_duplicates().tolist())

    return duplicate_itns, duplicate_slis


def build_itns_with_duplicate_sli_list(sli_map_df: pd.DataFrame):
    if sli_map_df.empty:
        return False, "SLI Map file is missing.", pd.DataFrame()

    itn_col = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)
    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"), None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)

    df = sli_map_df[sli_map_df[invoice_type_col].astype(str).str.strip().str.upper().eq("SLI")][[itn_col, invoice_number_col]].copy()

    duplicate_slis_df = (df.groupby(invoice_number_col).agg(ITN=(itn_col, lambda x: ", ".join(sorted(set(map(str, x)))))).reset_index().rename(columns={invoice_number_col: "SLI"}))

    duplicate_slis_df = duplicate_slis_df[duplicate_slis_df["ITN"].str.contains(",", regex=False)]

    return True, "", duplicate_slis_df[["ITN", "SLI"]]

def build_audit_summary_df(aes_df, gts_sli_df, sli_map_df):

    aes_df = aes_df.copy()
    gts_sli_df = gts_sli_df.copy()
    sli_map_df = sli_map_df.copy()

    if not AES_FILE.exists():
        return False, "AES file is missing. Do not proceed until attaining the file", pd.DataFrame()

    if not GTS_FILE.exists():
        return False, "GTS SLI is missing. Do not proceed until attaining the file", pd.DataFrame()
    
    if not SLI_MAP_FILE.exists():
        return False, "SLI Map is missing. Do not proceed until attaining the file", pd.DataFrame()

    aes_required = ["ITN", "Commodity Line Value", "Quantity 1"]

    gts_required = ["Item - Value (USD)","Item - Quantity Schedule B Unit(s)"]

    sli_required = ["ITN", "Invoice type", "Invoice number"]

    for col in aes_required:
        if col not in aes_df.columns:
            raise ValueError(f"AES missing column: {col}")

    for col in gts_required:
        if col not in gts_sli_df.columns:
            raise ValueError(f"GTS missing column: {col}")

    for col in sli_required:
        if col not in sli_map_df.columns:
            raise ValueError(f"SLI Map missing column: {col}")


    aes_df["AES Value"] = pd.to_numeric(aes_df["Commodity Line Value"].astype(str).str.replace(",", "", regex=False),errors="coerce").fillna(0)

    aes_df["AES Qty"] = pd.to_numeric(aes_df["Quantity 1"].astype(str).str.replace(",", "", regex=False),errors="coerce").fillna(0)

    gts_sli_df["GTS Value"] = pd.to_numeric(gts_sli_df["Item - Value (USD)"].astype(str).str.replace(",", "", regex=False),errors="coerce").fillna(0)

    gts_sli_df["GTS Qty"] = pd.to_numeric(gts_sli_df["Item - Quantity Schedule B Unit(s)"].astype(str).str.replace(",", "", regex=False), errors="coerce").fillna(0)

    # rename "Shipper's ref num" column to "SLI" column
    gts_sli_df = gts_sli_df.rename(columns={"Shipper's ref num": "SLI"})
    
    # Find required columns dynamically
    itn_col = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)

    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"), None)

    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)

    if not all([itn_col, invoice_type_col, invoice_number_col]):
        raise ValueError("SLI Map must contain ITN, Invoice Type, and Invoice Number columns")

    mapping_df = (sli_map_df[sli_map_df[invoice_type_col].astype(str).str.strip().str.upper().eq("SLI")][[itn_col, invoice_number_col]].copy())

    # Standardize column names
    mapping_df.columns = ["ITN", "SLI"]

    mapping_df["ITN"] = (mapping_df["ITN"].astype(str).str.strip())

    mapping_df["SLI"] = (mapping_df["SLI"].astype(str).str.strip())

    mapping_df = (mapping_df.replace("", pd.NA).dropna(subset=["ITN", "SLI"]).drop_duplicates())

    # Prevent one SLI mapping to multiple ITNs
    counts = mapping_df.groupby("SLI")["ITN"].nunique()

    ambiguous_slis = set(counts[counts > 1].index)

    mapping_df = mapping_df[~mapping_df["SLI"].isin(ambiguous_slis)]

    mapping_df = mapping_df.drop_duplicates(subset=["SLI"])

    gts_sli_df = gts_sli_df.drop(columns = ["ITN"], errors="ignore")
    gts_sli_df = pd.merge(
        gts_sli_df,
        mapping_df,
        how="left",
        on="SLI"
    )

    aes_summary = (
        aes_df
        .groupby("ITN", as_index=False)
        .agg(
            {
                "AES Value": "sum",
                "AES Qty": "sum"
            }
        )
    )
    
    gts_sli_summary = (
        gts_sli_df
        .groupby("ITN", as_index=False)
        .agg(
            {
                "GTS Value": "sum",
                "GTS Qty": "sum"
            }
        )
    )

    audit_df = pd.merge(
        aes_summary,
        gts_sli_summary,
        how="outer",
        on="ITN"
    )

    audit_df = audit_df.fillna(0)
    
    # Calculate the difference and compare with the threshold
    audit_df["Value Diff"] = (audit_df["AES Value"]- audit_df["GTS Value"]).abs()

    audit_df["Qty Diff"] = (audit_df["AES Qty"]- audit_df["GTS Qty"]).abs()

    audit_df["Value Audit"] = audit_df["Value Diff"].le(100).map(
        {True: "PASS", False: "FAIL"})

    audit_df["Qty Audit"] = audit_df["Qty Diff"].le(100).map(
        {True: "PASS", False: "FAIL"})
    
    # format
    for col in ["AES Value", "GTS Value", "Value Diff"]: audit_df[col] = audit_df[col].map(lambda x: f"${x:,.0f}")
    for col in ["AES Qty", "GTS Qty", "Qty Diff"]: audit_df[col] = audit_df[col].map(lambda x: f"{x:,.0f}")
    
    return True, "Aduit document created successfully. Please preview in DATA page", audit_df.sort_values("ITN")


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

def master_list_status(master_df: pd.DataFrame):
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
    has_at_least_one_doc = (
        (df["Packing-List file count"] > 0) & (df["AVL file count"] > 0) & (df["SLI file count"] > 0) & ((df["AWB file count"] > 0) | (df["SWB file count"] > 0))
    )

    # Number of AVL, Packing-List, and SLI must match
    counts_match = (
        (df["AVL file count"] == df["Packing-List file count"]) & (df["AVL file count"] == df["SLI file count"])
    )
    
    # ITNs with duplicated SLI check
    duplicate_itns, _ = find_itns_with_duplicate_slis(load_save(SLI_MAP_FILE))

    itns_with_duplicated_sli_list = (df[ITN_COL].astype(str).str.strip().isin(duplicate_itns)) 

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
    df["Document status"] = "FAIL"
    df.loc[has_at_least_one_doc & counts_match & swb_check & ~itns_with_duplicated_sli_list, "Document status"] = "PASS"

    # Reason for Doc status = Fail
    df["Missing SLI"] = (df["SLI file count"] == 0) | (df["SLI file count"] < df["APL file count"]) | (df["SLI file count"] < df["AVL file count"])
    df["Missing AVL"] = (df["AVL file count"] == 0) | (df["AVL file count"] < df["APL file count"]) | (df["AVL file count"] < df["SLI file count"])
    df["Missing Packing List"] = df["Packing-List file count"] == 0 | (df["Packing-List file count"] < df["SLI file count"]) | (df["Packing-List file count"] < df["AVL file count"])
    df["Missing APL"] = df["APL file count"] == 0
    df["No AWB/SWB"] = (df["AWB file count"] == 0) & (df["SWB file count"] == 0)
    df["Number of document doesn't match (missing doc)"] = ~counts_match
    df["ITN with swb not in Sea Export"] = swb_exist & ~swb_valid
    df["ITN with duplicated SLI with another ITN"] = itns_with_duplicated_sli_list


    error_cols = [
    col for col in [
        ITN_COL,
        "Missing SLI",
        "Missing AVL",
        "Missing Packing List",
        "No AWB/SWB",
        "Number of document doesn't match (missing doc)",
        "ITN with swb not in Sea Export",
        "ITN with duplicated SLI with another ITN"
        ]
    if col in df.columns]

    doc_not_ready_df = (
        df.loc[df["Document status"] == "FAIL", error_cols].drop_duplicates().reset_index(drop=True)
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

    df["Audit status"] = "FAIL"
    df.loc[df[ITN_COL].astype(str).isin(audit_ready_itns), "Audit status"] = "PASS"

    # Next step guidance
    df["Next Step"] = ""
    df.loc[(df["SLI file count"] == 0) & (df["AVL file count"] == 0) & (df["Packing-List file count"] == 0) & df["No AWB/SWB"], "Next Step"] += "Scrape documents, "
    df.loc[((df["SLI file count"] < df["APL file count"]) & (df["AVL file count"] < df["APL file count"])) | 
        ((df["SLI file count"] < df["Packing-List file count"]) & (df["AVL file count"] < df["Packing-List file count"])), "Next Step"] += "Run intercompany cockpit using APL, "
    df.loc[(df["SLI file count"] < df["AVL file count"]) | (df["AVL file count"] < df["SLI file count"]), "Next Step"] += "Use SAP (check Output), "
    df.loc[df["Missing Packing List"] & has_at_least_one_doc, "Next Step"] += "Contact Kolby to get PL, "
    df.loc[df["ITN with duplicated SLI with another ITN"] | (df["No AWB/SWB"] & ((df["SLI file count"] > 0) | (df["AVL file count"] > 0) | (df["Packing-List file count"] > 0))) | df["ITN with swb not in Sea Export"], "Next Step"] += "Contact brokers (check Output), "
    df["Next Step"] =  df["Next Step"].str.rstrip(", ")

    return df, doc_not_ready_df, doc_not_ready_itns, audit_ready_df, audit_ready_itns

def build_contact_brokers_df():
    output_cols = ["ITN", "Shipment Reference Number", "Reason"]

    aes_df = load_save(AES_FILE)
    doc_df = load_save(DOC_SEARCH_FILE)

    if aes_df.empty or doc_df.empty:
        return pd.DataFrame(columns=output_cols)

    aes_itn_col = next((col for col in aes_df.columns if col.lower() == "itn"), None)
    doc_itn_col = next((col for col in doc_df.columns if col.lower() == "itn"), None)

    shipment_ref_col = next(
        (col for col in aes_df.columns if col.lower() == "shipment reference number"),
        None,
    )

    if aes_itn_col is None or doc_itn_col is None or shipment_ref_col is None:
        return pd.DataFrame(columns=output_cols)

    aes_df = aes_df.copy()
    doc_df = doc_df.copy()

    aes_df[aes_itn_col] = aes_df[aes_itn_col].astype(str).str.strip()
    doc_df[doc_itn_col] = doc_df[doc_itn_col].astype(str).str.strip()

    # Assign ITN in AES to Doc Search
    working_master_df = aes_df.merge(
        doc_df,
        left_on=aes_itn_col,
        right_on=doc_itn_col,
        how="left"
    )

    if doc_itn_col in working_master_df.columns and doc_itn_col != "ITN":
        working_master_df = working_master_df.drop(
            columns=[doc_itn_col],
            errors="ignore"
        )

    (df, doc_not_ready_df, doc_not_ready_itns,audit_ready_df, audit_ready_itns) = master_list_status(working_master_df)

    if doc_not_ready_df.empty:
        return pd.DataFrame(columns=output_cols)

    # Build summary table
    summary_df = (df[["ITN", "Document status", "Audit status", "Next Step"]].drop_duplicates())

    # Only ITNs whose Next Step is exactly Contact brokers
    broker_itns = (summary_df.loc[summary_df["Next Step"].astype(str).str.strip().eq("Contact brokers (check Output)"),"ITN",].astype(str).str.strip().drop_duplicates())

    if broker_itns.empty:
        return pd.DataFrame(columns=output_cols)

    contact_broker_reason_cols = [
        "ITN with duplicated SLI with another ITN",
        "No AWB/SWB",
        "ITN with swb not in Sea Export",
    ]

    existing_reason_cols = [
        col
        for col in contact_broker_reason_cols
        if col in doc_not_ready_df.columns
    ]

    if not existing_reason_cols:
        return pd.DataFrame(columns=output_cols)

    broker_contact_df = (doc_not_ready_df[doc_not_ready_df["ITN"].astype(str).str.strip().isin(set(broker_itns))][["ITN"] + existing_reason_cols].copy())

    if broker_contact_df.empty:
        return pd.DataFrame(columns=output_cols)

    def is_true_value(value):
        if isinstance(value, bool):
            return value

        return str(value).strip().lower() in ["true", "1", "yes"]

    def get_reason(row):
        reasons = []

        for col in existing_reason_cols:
            if is_true_value(row[col]):
                reasons.append(col)

        return ", ".join(reasons)

    broker_contact_df["Reason"] = broker_contact_df.apply(get_reason,axis=1)

    broker_contact_df = broker_contact_df[broker_contact_df["Reason"].astype(str).str.strip()!= ""][["ITN", "Reason"]]

    if broker_contact_df.empty:
        return pd.DataFrame(columns=output_cols)

    # Add Shipment Reference Number from AES
    aes_lookup_df = aes_df[[aes_itn_col, shipment_ref_col]].copy()

    aes_lookup_df[aes_itn_col] = (aes_lookup_df[aes_itn_col].astype(str).str.strip())

    aes_lookup_df = (aes_lookup_df.drop_duplicates().rename(columns={aes_itn_col: "ITN",shipment_ref_col: "Shipment Reference Number",}))

    broker_contact_df = broker_contact_df.merge(aes_lookup_df, on="ITN", how="left")

    broker_contact_df["Shipment Reference Number"] = (broker_contact_df["Shipment Reference Number"].fillna(""))

    return (broker_contact_df[output_cols].drop_duplicates().reset_index(drop=True))

def build_sap_download_df():
    sap_download_cols = ["ITN", "Doc to download", "Input"]

    doc_df = load_save(DOC_SEARCH_FILE)
    sli_map_df = load_save(SLI_MAP_FILE)

    if doc_df.empty or sli_map_df.empty:
        return pd.DataFrame(columns=sap_download_cols)

    doc_itn_col = next((col for col in doc_df.columns if col.lower() == "itn"), None)
    sli_count_col = next((col for col in doc_df.columns if col.lower() == "sli file count"), None)
    avl_count_col = next((col for col in doc_df.columns if col.lower() == "avl file count"), None)

    map_itn_col = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)
    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"), None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)

    required_cols = [
        doc_itn_col,
        sli_count_col,
        avl_count_col,
        map_itn_col,
        invoice_type_col,
        invoice_number_col,
    ]

    if any(col is None for col in required_cols):
        return pd.DataFrame(columns=sap_download_cols)

    doc_df = doc_df.copy()
    sli_map_df = sli_map_df.copy()

    doc_df[doc_itn_col] = doc_df[doc_itn_col].astype(str).str.strip()
    sli_map_df[map_itn_col] = sli_map_df[map_itn_col].astype(str).str.strip()

    doc_df[sli_count_col] = pd.to_numeric(doc_df[sli_count_col],errors="coerce").fillna(0).astype(int)

    doc_df[avl_count_col] = pd.to_numeric(doc_df[avl_count_col],errors="coerce").fillna(0).astype(int)

    sli_map_df[invoice_type_col] = (sli_map_df[invoice_type_col].astype(str).str.strip().str.upper())

    sli_map_df[invoice_number_col] = (sli_map_df[invoice_number_col].astype(str).str.strip())

    # Only ITNs where SLI and AVL counts do not match
    mismatch_df = doc_df.loc[doc_df[sli_count_col] != doc_df[avl_count_col],[doc_itn_col, sli_count_col, avl_count_col]].copy()

    if mismatch_df.empty:
        return pd.DataFrame(columns=sap_download_cols)

    sap_download_rows = []

    for _, row in mismatch_df.iterrows():
        itn = str(row[doc_itn_col]).strip()
        sli_count = row[sli_count_col]
        avl_count = row[avl_count_col]

        itn_map_df = sli_map_df[sli_map_df[map_itn_col].astype(str).str.strip().eq(itn)].copy()

        sli_numbers = (itn_map_df.loc[itn_map_df[invoice_type_col].eq("SLI"),invoice_number_col].replace("", pd.NA).dropna().drop_duplicates().tolist())

        avl_numbers = (
            itn_map_df.loc[itn_map_df[invoice_type_col].eq("AVL"),invoice_number_col].replace("", pd.NA).dropna().drop_duplicates().tolist())

        sli_set = set(sli_numbers)
        avl_set = set(avl_numbers)

        if sli_count > avl_count:
            doc_to_download = "avl"

            # SLI exists but matching AVL is missing
            odd_inputs = [invoice_number for invoice_number in sli_numbers if invoice_number not in avl_set]

        elif avl_count > sli_count:
            doc_to_download = "sli"

            # AVL exists but matching SLI is missing
            odd_inputs = [invoice_number for invoice_number in avl_numbers if invoice_number not in sli_set]
        else:
            continue

        for input_value in odd_inputs:
            sap_download_rows.append({
                "ITN": itn, "Doc to download": doc_to_download, "Input": input_value,})

    return (pd.DataFrame(sap_download_rows, columns=sap_download_cols).drop_duplicates().reset_index(drop=True))

def build_run_intercompany_cockpit():
    build_run_intercompany_cols = ["ITN", "APL"]

    aes_df = load_save(AES_FILE)
    doc_df = load_save(DOC_SEARCH_FILE)
    sli_map_df = load_save(SLI_MAP_FILE)

    if aes_df.empty or doc_df.empty or sli_map_df.empty:
        return pd.DataFrame(columns=build_run_intercompany_cols)

    aes_itn_col = next((col for col in aes_df.columns if col.lower() == "itn"), None)
    doc_itn_col = next((col for col in doc_df.columns if col.lower() == "itn"), None)
    map_itn_col = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)

    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"), None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)

    required_cols = [
        aes_itn_col,
        doc_itn_col,
        map_itn_col,
        invoice_type_col,
        invoice_number_col,
    ]

    if any(col is None for col in required_cols):
        return pd.DataFrame(columns=build_run_intercompany_cols)

    aes_df = aes_df.copy()
    doc_df = doc_df.copy()
    sli_map_df = sli_map_df.copy()

    aes_df[aes_itn_col] = aes_df[aes_itn_col].astype(str).str.strip()
    doc_df[doc_itn_col] = doc_df[doc_itn_col].astype(str).str.strip()

    # Build working master df (same approach as build_contact_brokers_df)
    working_master_df = aes_df.merge(
        doc_df,
        left_on=aes_itn_col,
        right_on=doc_itn_col,
        how="left"
    )

    if aes_itn_col != "ITN":
        working_master_df = working_master_df.rename(
            columns={aes_itn_col: "ITN"}
        )

    if doc_itn_col in working_master_df.columns and doc_itn_col != "ITN":
        working_master_df = working_master_df.drop(
            columns=[doc_itn_col],
            errors="ignore"
        )

    (df, doc_not_ready_df, doc_not_ready_itns, audit_ready_df,audit_ready_itns) = master_list_status(working_master_df)

    summary_df = (df[["ITN", "Document status", "Audit status", "Next Step"]].drop_duplicates())

    itns_need_to_run_intercompany = (summary_df.loc[summary_df["Next Step"].astype(str).str.contains("Run intercompany cockpit using APL",case=False,na=False),"ITN"].astype(str).str.strip().drop_duplicates())

    if itns_need_to_run_intercompany.empty:
        return pd.DataFrame(columns=build_run_intercompany_cols)

    sli_map_df[map_itn_col] = (sli_map_df[map_itn_col].astype(str).str.strip())

    sli_map_df[invoice_type_col] = (sli_map_df[invoice_type_col].astype(str).str.strip().str.upper())

    sli_map_df[invoice_number_col] = (sli_map_df[invoice_number_col].astype(str).str.strip())

    build_run_intercompany_df = (
        sli_map_df[
            (sli_map_df[map_itn_col].isin(set(itns_need_to_run_intercompany))) &
            (sli_map_df[invoice_type_col] == "APL")
            ][[map_itn_col, invoice_number_col]].drop_duplicates().groupby(map_itn_col, as_index = False).agg({invoice_number_col: lambda x: ", ".join(sorted(
            set(str(v).strip()
            for v in x
            if str(v).strip())))}).rename(
            columns={map_itn_col: "ITN", invoice_number_col: "APL"}).reset_index(drop=True))

    return build_run_intercompany_df

