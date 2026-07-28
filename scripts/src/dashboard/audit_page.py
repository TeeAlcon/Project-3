import pandas as pd
import streamlit as st
from utils.file_analyzed import (load_save, save_csv)
from services.audit_status import build_audit_summary_df

from config import (AES_FILE, GTS_FILE, SLI_MAP_FILE, AUDIT_FILE)

from components.table_styles import (highlight_fail_rows)


def render():
    st.title("Audit Doc Generator")

    aes_df = (load_save(AES_FILE))
    gts_sli_df = (load_save(GTS_FILE))
    sli_map_df = (load_save(SLI_MAP_FILE))

    gts_sli_df = gts_sli_df.rename(columns={"Shipper's ref num": "SLI"})

    success, message, audit_df = (build_audit_summary_df(aes_df,gts_sli_df,sli_map_df))

    if not success:
        st.error(message)

    else:
        save_csv(audit_df, AUDIT_FILE)

        st.success(message)

        st.dataframe(
            audit_df.style.apply(
                highlight_fail_rows,
                axis=1
            ), use_container_width=True)