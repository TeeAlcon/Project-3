import hashlib
import pandas as pd

from utils.file_utils import (load_save, normalize_columns, save_csv)
from config import REQUIRED_COLS_FOR_CONFIG

# Stable fingerprint for all rows in one ID group
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

def analyze_hierarchical_import(save_df: pd.DataFrame, import_df: pd.DataFrame, id_col: str):
    if id_col not in import_df.columns:
        raise ValueError(f"Upload missing ID column: {id_col}")

    if len(save_df) and id_col not in save_df.columns:
        raise ValueError(f"Save missing ID column: {id_col}")

    import_df = import_df.copy()
    save_df = save_df.copy()

    # Normalize ID column
    import_df[id_col] = (import_df[id_col].fillna("").astype(str).str.strip())

    if len(save_df):
        save_df[id_col] = (save_df[id_col].fillna("").astype(str).str.strip())

    # SLI headers are rows where Number is populated
    import_slis = set(import_df.loc[import_df[id_col] != "", id_col])

    save_slis = set()

    if not save_df.empty:
        save_slis = set(save_df.loc[save_df[id_col] != "", id_col])

    # New SLI IDs only
    new_slis = import_slis - save_slis

    rows_added = pd.DataFrame(columns=import_df.columns)

    if new_slis:

        collected_rows = []
        current_sli = None

        for _, row in import_df.iterrows():

            sli = row[id_col]

            # New SLI block begins
            if sli != "":
                current_sli = sli

            # Keep entire block belonging to a new SLI
            if current_sli in new_slis:
                collected_rows.append(row)

        rows_added = pd.DataFrame(collected_rows)

    updated_df = pd.concat([save_df, rows_added], ignore_index=True)

    return updated_df, rows_added

# file uploaded must have certain headers to be considered for a report
def validate_report_structure(df, base_file):
    required_cols = REQUIRED_COLS_FOR_CONFIG.get(base_file, set())

    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        return False, (f"Missing required columns. Please ensure you are uploading the file with correct configuration")

    return True, ""

def process_upload(import_df, save_path, id_col):
    save_df = load_save(save_path)

    updated_df, changed_rows = analyze_import(save_df, import_df, id_col)

    save_csv(updated_df, save_path)

    return updated_df, changed_rows