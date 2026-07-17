import pandas as pd

import utils.update_data_detection as update_data_detection

from config import REPORTS


def build_status_df():
    status = []

    for report in REPORTS.values():

        path = report["path"]

        df = update_data_detection.load_save(path)

        status.append({
            "Report": report["title"],
            "Loaded": "Yes" if path.exists() else "No",
            "Rows": len(df),
            "Columns": len(df.columns),
        })

    return pd.DataFrame(status)