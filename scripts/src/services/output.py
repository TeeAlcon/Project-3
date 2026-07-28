import streamlit as st
import pandas as pd
from config import (AES_FILE, DOC_SEARCH_FILE, SLI_MAP_FILE)
from utils.file_utils import load_save

def build_contact_brokers_df(summary_df: pd.DataFrame, doc_fail_df: pd.DataFrame):
    output_cols = [
        "ITN",
        "Shipment Reference Number",
        "Reason"
    ]

    if doc_fail_df.empty or summary_df.empty:
        return pd.DataFrame(columns=output_cols)

    aes_df = load_save(AES_FILE)

    if aes_df.empty:
        return pd.DataFrame(columns=output_cols)


    # Keep only ITNs flagged for broker contact
    need_contact_itns = (
        summary_df.loc[summary_df["Next Step"].astype(str).str.strip() == "Contact brokers (check OUTPUT)", "ITN"].astype(str).str.strip().unique())

    if len(need_contact_itns) == 0:
        return pd.DataFrame(columns=output_cols)

    contact_broker_df = doc_fail_df.copy()
    contact_broker_df["ITN"] = (contact_broker_df["ITN"].astype(str).str.strip())

    contact_broker_df = contact_broker_df[contact_broker_df["ITN"].isin(need_contact_itns)]

    if contact_broker_df.empty:
        return pd.DataFrame(columns=output_cols)

    reason_cols = [
        "Duplicate SLI",
        "No AWB/SWB",
        "SWB Missing From Sea Export",
    ]

    doc_fail_reason_cols = [col for col in reason_cols if col in contact_broker_df.columns]

    if not doc_fail_reason_cols:
        return pd.DataFrame(columns=output_cols)

    def is_true_value(value):
        if isinstance(value, bool):
            return value
        return str(value).strip().upper() == "TRUE"

    # Keep rows where at least one reason column is TRUE
    mask = contact_broker_df[doc_fail_reason_cols].apply(lambda row: any(is_true_value(v) for v in row), axis=1)

    contact_broker_df = contact_broker_df.loc[mask].copy()

    if contact_broker_df.empty:
        return pd.DataFrame(columns=output_cols)

    def get_reason(row):
        reasons = []
        for col in doc_fail_reason_cols:
            if is_true_value(row[col]):
                reasons.append(col)
        return ", ".join(reasons)

    contact_broker_df["Reason"] = contact_broker_df.apply(get_reason, axis=1)

    # AES lookup for Shipment Reference Number
    aes_lookup_df = (aes_df[["ITN", "Shipment Reference Number"]].copy())

    aes_lookup_df["ITN"] = (aes_lookup_df["ITN"].astype(str).str.strip())

    aes_lookup_df = aes_lookup_df.drop_duplicates()

    contact_broker_df = (contact_broker_df.drop(columns=["Shipment Reference Number"], errors="ignore").merge(aes_lookup_df, on="ITN", how="left"))

    contact_broker_df["Shipment Reference Number"] = (contact_broker_df["Shipment Reference Number"].fillna(""))

    return (contact_broker_df[output_cols].drop_duplicates().reset_index(drop=True))


def build_sap_download_df():
    output_cols = ["ITN", "Doc to download", "Input"]

    doc_df = load_save(DOC_SEARCH_FILE)
    sli_map_df = load_save(SLI_MAP_FILE)

    if doc_df.empty or sli_map_df.empty:
        return pd.DataFrame(columns=output_cols)

    doc_itn_col = "ITN"

    sli_count_col = "SLI file count"
    avl_count_col = "AVL file count"

    map_itn_col = "ITN"

    invoice_type_col = "Invoice type"
    invoice_number_col = "Invoice number"

    required_cols = [
        doc_itn_col,
        sli_count_col,
        avl_count_col,
        map_itn_col,
        invoice_type_col,
        invoice_number_col,
    ]

    all_cols_exist = all(
        col in doc_df.columns
        or col in sli_map_df.columns
        for col in required_cols
    )

    if not all_cols_exist:
        return pd.DataFrame(columns=output_cols)

    doc_df = doc_df.copy()
    sli_map_df = sli_map_df.copy()

    doc_df[sli_count_col] = (
        pd.to_numeric(
            doc_df[sli_count_col],
            errors="coerce").fillna(0).astype(int))

    doc_df[avl_count_col] = (
        pd.to_numeric(
            doc_df[avl_count_col],
            errors="coerce",
        ).fillna(0).astype(int))

    mismatch_df = doc_df.loc[
        doc_df[sli_count_col]
        != doc_df[avl_count_col]
    ]

    if mismatch_df.empty:
        return pd.DataFrame(columns=output_cols)

    rows = []

    for _, row in mismatch_df.iterrows():

        itn = str(row[doc_itn_col]).strip()

        sli_count = row[sli_count_col]
        avl_count = row[avl_count_col]

        itn_map_df = sli_map_df.loc[sli_map_df[map_itn_col].astype(str).str.strip().eq(itn)]

        sli_numbers = (itn_map_df.loc[itn_map_df[invoice_type_col].astype(str).str.upper().eq("SLI"),invoice_number_col].dropna().astype(str).unique())

        avl_numbers = (itn_map_df.loc[itn_map_df[invoice_type_col].astype(str).str.upper().eq("AVL"), invoice_number_col].dropna().astype(str).unique())

        sli_set = set(sli_numbers)
        avl_set = set(avl_numbers)

        if sli_count > avl_count:

            doc_type = "avl"

            missing_docs = [value for value in sli_numbers if value not in avl_set]

        elif avl_count > sli_count:

            doc_type = "sli"

            missing_docs = [value for value in avl_numbers if value not in sli_set]

        else:
            continue

        for value in missing_docs:

            rows.append(
                {
                    "ITN": itn,
                    "Doc to download": doc_type,
                    "Input": value,
                }
            )

    return (pd.DataFrame(rows).drop_duplicates().reset_index(drop=True))

@st.cache_data
def build_run_intercompany_cockpit_df(sli_map_df):
    output_cols = ["ITN", "APL"]

    if sli_map_df.empty:
        return pd.DataFrame(columns=output_cols)

    map_itn_col = "ITN"
    invoice_type_col = "Invoice type"
    invoice_number_col = "Invoice number"

    apl_df = (
        sli_map_df.loc[(sli_map_df[invoice_type_col].astype(str).str.upper().eq("APL"))].reset_index().rename(columns={map_itn_col: "ITN", invoice_number_col: "APL"}))

    return (apl_df[output_cols].drop_duplicates().reset_index(drop=True))