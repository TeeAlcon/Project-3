import streamlit as st

import utils.update_data_detection as update_data_detection

from config import (
    AES_FILE,
    GTS_FILE,
    SLI_MAP_FILE,
    AUDIT_DOC_FILE,
)

from components.table_styles import (
    highlight_fail_rows
)


def render():
    st.title("Audit Doc Generator")

    aes_df = (update_data_detection.load_save(AES_FILE))
    gts_sli_df = (update_data_detection.load_save(GTS_FILE))
    sli_map_df = (update_data_detection.load_save(SLI_MAP_FILE))

    gts_sli_df = gts_sli_df.rename(columns={"Shipper's ref num": "SLI"})

    success, message, audit_df = (update_data_detection.build_audit_summary_df(aes_df,gts_sli_df,sli_map_df))

    if not success:
        st.error(message)

    else:
        update_data_detection.save_csv(audit_df,AUDIT_DOC_FILE)

        st.success(message)

        st.dataframe(
            audit_df.style.apply(
                highlight_fail_rows,
                axis=1
            ),
            use_container_width=True
        )