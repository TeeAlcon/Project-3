import streamlit as st
import pandas as pd
from config import AUDIT_FILE
from utils.file_utils import load_save


def parse_audit_number(series):
    return (
        pd.to_numeric(
            series.astype(str)
            .str.replace(r"[\$,]", "", regex=True)
            .str.strip(),
            errors="coerce",
        )
        .fillna(0)
    )

@st.cache_data
def build_audit_summary_df(aes_df, gts_sli_df, sli_map_df):
    aes_df = aes_df.copy()
    gts_sli_df = gts_sli_df.copy()
    sli_map_df = sli_map_df.copy()

    if aes_df.empty:
        return False, "AES file is missing. Do not proceed until obtaining the file", pd.DataFrame()
    if gts_sli_df.empty:
        return False, "GTS SLI is missing. Do not proceed until obtaining the file", pd.DataFrame() 
    if sli_map_df.empty:
        return False, "SLI Map is missing. Do not proceed until obtaining the file", pd.DataFrame()

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

    aes_summary = (aes_df.groupby("ITN", as_index=False).agg({"AES Value": "sum", "AES Qty": "sum"}))
    
    gts_sli_summary = (gts_sli_df.groupby("ITN", as_index=False).agg({"GTS Value": "sum", "GTS Qty": "sum"}))

    audit_df = pd.merge(
        aes_summary,
        gts_sli_summary,
        how="outer",
        on="ITN"
    )

    audit_df = audit_df.fillna(0)


    # Calculate the difference and compare with the threshold
    audit_df["Value Diff"] = (audit_df["AES Value"]- audit_df["GTS Value"]).abs()
    audit_df["Value Diff"] = parse_audit_number(audit_df["Value Diff"])

    audit_df["Qty Diff"] = (audit_df["AES Qty"]- audit_df["GTS Qty"]).abs()

    audit_df["Value Audit"] = audit_df["Value Diff"].le(100).map(
        {True: "PASS", False: "FAIL"})

    audit_df["Qty Audit"] = audit_df["Qty Diff"].le(100).map(
        {True: "PASS", False: "FAIL"})
    
    # format
    for col in ["AES Value", "GTS Value", "Value Diff"]: audit_df[col] = audit_df[col].map(lambda x: f"${x:,.0f}")
    for col in ["AES Qty", "GTS Qty", "Qty Diff"]: audit_df[col] = audit_df[col].map(lambda x: f"{x:,.0f}")
    
    return True, "Audit document created successfully. Please preview in DATA page", audit_df.sort_values("ITN")


def evaluate_audit_status(master_df):

    df = master_df.copy()

    df["Audit Status"] = "FAIL"

    audit_df = load_save(AUDIT_FILE)

    if audit_df.empty:
        return df

    audit_itns = (audit_df.loc[(audit_df["Value Audit"] == "PASS") & (audit_df["Qty Audit"] == "PASS"), "ITN"].astype(str).str.strip().drop_duplicates().tolist())

    df.loc[df["ITN"].astype(str).isin(audit_itns), "Audit Status"] = "PASS"

    return df
