import streamlit as st
import pandas as pd

@st.cache_data
def find_map_sli_not_in_gts(gts_sli_df: pd.DataFrame, sli_map_df: pd.DataFrame):
    gts_sli_df = gts_sli_df.rename(columns={"Shipper's ref num": "SLI"})
    gts_sli_col = next((col for col in gts_sli_df.columns if col.lower() == "sli"), None)
    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"), None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)
    corresponding_itn_col = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)

    # Extract only SLI records from Invoice Number in Map SLI    
    sli_df = sli_map_df[sli_map_df[invoice_type_col].astype(str).str.strip().str.upper().eq("SLI")].copy()
    gts_sli_df[gts_sli_col] = (gts_sli_df[gts_sli_col].astype(str).str.strip())

    sli_df[invoice_number_col] = (sli_df[invoice_number_col].astype(str).str.strip())

    mapped_sli_set = (gts_sli_df[gts_sli_col].replace("", pd.NA).dropna().drop_duplicates())

    unmapped_sli_df = (
        sli_df[~sli_df[invoice_number_col].isin(mapped_sli_set)][[corresponding_itn_col, invoice_number_col]].drop_duplicates().rename(columns={corresponding_itn_col: "ITN", invoice_number_col: "SLI"}).reset_index(drop=True)
    )

    return unmapped_sli_df

@st.cache_data
# Assign SLI in map to SLI in Export Dec
def find_map_sli_not_in_export_dec(export_dec_df: pd.DataFrame, sli_map_df: pd.DataFrame):
    export_dec_sli_col = export_dec_df.columns[0] # Only for Export Decleration, the first column will always be SLI col

    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"), None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)
    corresponding_itn_col = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)

    sli_df = sli_map_df[sli_map_df[invoice_type_col].astype(str).str.strip().str.upper().eq("SLI")].copy()
    export_dec_df[export_dec_sli_col] = (export_dec_df[export_dec_sli_col].astype(str).str.strip())

    sli_df[invoice_number_col] = (sli_df[invoice_number_col].astype(str).str.strip())

    in_dec_sli_set = (export_dec_df[export_dec_sli_col].replace("", pd.NA).dropna().drop_duplicates())

    not_in_dec_sli_df = (
        sli_df[~sli_df[invoice_number_col].isin(in_dec_sli_set)][[corresponding_itn_col, invoice_number_col]].drop_duplicates().rename(columns={corresponding_itn_col: "ITN", invoice_number_col: "SLI"}).reset_index(drop=True)
    )

    return not_in_dec_sli_df

@st.cache_data
def find_itns_with_duplicate_slis(sli_map_df: pd.DataFrame):
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

@st.cache_data
def build_itns_with_duplicate_sli_list(sli_map_df: pd.DataFrame): 
    itn_col = next((col for col in sli_map_df.columns if col.lower() == "itn"), None)
    invoice_type_col = next((col for col in sli_map_df.columns if col.lower() == "invoice type"), None)
    invoice_number_col = next((col for col in sli_map_df.columns if col.lower() == "invoice number"), None)

    df = sli_map_df[sli_map_df[invoice_type_col].astype(str).str.strip().str.upper().eq("SLI")][[itn_col, invoice_number_col]].copy()

    duplicate_slis_df = (df.groupby(invoice_number_col).agg(ITN=(itn_col, lambda x: ", ".join(sorted(set(map(str, x)))))).reset_index().rename(columns={invoice_number_col: "SLI"}))

    duplicate_slis_df = duplicate_slis_df[duplicate_slis_df["ITN"].str.contains(",", regex=False)]

    return duplicate_slis_df[["ITN", "SLI"]]
