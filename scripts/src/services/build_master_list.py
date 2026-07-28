import streamlit as st
from utils.find_columns import find_column

@st.cache_data
def build_master_list_df(aes_df, doc_df):
    itn_col = find_column(doc_df, "ITN")

    aes_df[itn_col] = (
        aes_df[itn_col]
        .astype(str)
        .str.strip()
    )

    doc_df[itn_col] = (
        doc_df[itn_col]
        .astype(str)
        .str.strip()
    )

    master_df = aes_df.merge(doc_df, on=itn_col, how="left")

    return (True,"Master List updated with Doc Search and Audit data", master_df)