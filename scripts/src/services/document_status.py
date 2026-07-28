import streamlit as st
import pandas as pd
from config import (SEA_EXPORT_FILE, SLI_MAP_FILE)
from utils.file_utils import load_save
from services.mapping import find_itns_with_duplicate_slis


def evaluate_document_status(master_df: pd.DataFrame):
    if master_df.empty:
        return master_df.copy()

    df = master_df.copy()

    ITN_COL = "ITN"

    required_count_cols = [
        "Total PDF count",
        "SLI file count",
        "AVL file count",
        "APL file count",
        "Packing-List file count",
        "AWB file count",
        "SWB file count",
    ]

    # Ensure columns exist
    for col in required_count_cols:
        if col not in df.columns:
            df[col] = 0

    # Convert to numeric
    for col in required_count_cols:
        df[col] = (pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int))

    # Required document check
    has_required_docs = ((df["SLI file count"] > 0) & (df["AVL file count"] > 0) & (df["Packing-List file count"] > 0) & ((df["AWB file count"] > 0) | (df["SWB file count"] > 0)))

    # Counts must match
    counts_match = ((df["SLI file count"] == df["AVL file count"]) & (df["AVL file count"] == df["Packing-List file count"]))

    # Duplicate SLI validation
    duplicate_itns = []

    sli_map_df = load_save(SLI_MAP_FILE)

    if not sli_map_df.empty:
        duplicate_itns, _ = (find_itns_with_duplicate_slis(sli_map_df))

    duplicate_sli_check = (df[ITN_COL].astype(str).str.strip().isin(duplicate_itns))

    # Sea Export validation
    swb_exists = df["SWB file count"] > 0

    swb_valid = pd.Series(True, index=df.index)

    sea_df = load_save(SEA_EXPORT_FILE)

    if not sea_df.empty:

        sea_itn_col = next(
            (
                col
                for col in sea_df.columns
                if col.lower().strip() == "itn"
            ),
            None,
        )

        if sea_itn_col:

            sea_itns = set(
                sea_df[sea_itn_col]
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
            )

            swb_valid = (
                df[ITN_COL]
                .astype(str)
                .str.strip()
                .isin(sea_itns)
            )
        else:
            swb_valid = False

    swb_check = (~swb_exists) | (swb_exists & swb_valid)

    # Failure flags

    df["Missing SLI"] = (
        (df["SLI file count"] == 0) | (df["SLI file count"] < df["AVL file count"]) | (df["SLI file count"] < df["APL file count"]))

    df["Missing AVL"] = (
        (df["AVL file count"] == 0) | (df["AVL file count"] < df["SLI file count"]) | (df["AVL file count"] < df["APL file count"]))

    df["Missing Packing List"] = (
        (df["Packing-List file count"] == 0) 
        | (df["Packing-List file count"] < df["SLI file count"])
        | (df["Packing-List file count"]< df["AVL file count"]))

    df["Missing APL"] = (df["APL file count"] == 0)

    df["No AWB/SWB"] = ((df["AWB file count"] == 0) & (df["SWB file count"] == 0))

    df["Document Counts Mismatch"] = (~counts_match)

    df["SWB Missing From Sea Export"] = (swb_exists & ~swb_valid)

    df["Duplicate SLI"] = (duplicate_sli_check)

    # Final document status
    document_pass = (has_required_docs & counts_match & swb_check& ~duplicate_sli_check)

    df["Document Status"] = "FAIL"

    df.loc[document_pass, "Document Status"] = "PASS"

    return df

@st.cache_data
def build_document_error_df(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame()

    error_cols = [
        "ITN",
        "Missing SLI",
        "Missing AVL",
        "Missing Packing List",
        "Missing APL",
        "No AWB/SWB",
        "Document Counts Mismatch",
        "SWB Missing From Sea Export",
        "Duplicate SLI"
    ]

    existing_cols = [col for col in error_cols if col in df.columns]

    return (df.loc[df["Document Status"] == "FAIL", existing_cols,].drop_duplicates().reset_index(drop=True))

@st.cache_data
def get_document_fail_itns(df: pd.DataFrame):
    if (df.empty or "ITN" not in df.columns):
        return []

    return (df.loc[df["Document Status"] == "FAIL", "ITN"].astype(str).str.strip().replace("", pd.NA).dropna().drop_duplicates().tolist())

@st.cache_data
def generate_next_steps(df: pd.DataFrame):
    if df.empty:
        return df.copy()

    df = df.copy()

    if "Next Step" not in df.columns:
        df["Next Step"] = ""

    df.loc[(df["SLI file count"] == 0) & (df["AVL file count"] == 0) & (df["Packing-List file count"] == 0) & (df["No AWB/SWB"]), "Next Step"] += "Scrape documents, "

    df.loc[(((df["SLI file count"] < df["APL file count"]) & (df["AVL file count"] < df["APL file count"])) | ((df["SLI file count"] < df["Packing-List file count"])
          & (df["AVL file count"] < df["Packing-List file count"]))), "Next Step"] += "Run intercompany cockpit using APL, "

    df.loc[((df["SLI file count"] < df["AVL file count"]) | (df["AVL file count"] < df["SLI file count"])), "Next Step"] += "Use SAP (check OUTPUT), "

    df.loc[(df["Missing Packing List"] & ~df["No AWB/SWB"]),"Next Step"] += "Contact Kolby to get PL, "

    df.loc[(df["Duplicate SLI"] | (df["No AWB/SWB"] & (df["Total PDF count"] != 0)) | df["SWB Missing From Sea Export"]), "Next Step"] += "Contact brokers (check OUTPUT), "

    df["Next Step"] = (df["Next Step"].astype(str).str.rstrip(", "))

    return df