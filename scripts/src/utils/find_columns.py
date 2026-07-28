def find_column(df, column_name):
    return next((col for col in df.columns if col.lower().strip() == column_name.lower().strip()), None)


def get_sli_map_columns(df):
    return {
        "itn": find_column(df, "ITN"),
        "invoice_type": find_column(df, "Invoice Type"),
        "invoice_number": find_column(df, "Invoice Number"),
    }