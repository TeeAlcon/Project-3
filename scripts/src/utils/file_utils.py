import pandas as pd

def clean_columns(df):
    df.columns = df.columns.str.strip().str.replace("\xa0", " ", regex=False)
    return df

def read_csv(file_or_path):
    try:
        return (pd.read_csv(file_or_path, dtype=str, keep_default_na=False).fillna(""))
    except UnicodeDecodeError:
        return (pd.read_csv(file_or_path, dtype=str, keep_default_na=False, encoding="cp1252").fillna(""))

def save_csv(df, path):
    df.to_csv(path, index=False, encoding="utf-8-sig")

def load_save(path):
    return read_csv(path) if path.exists() else pd.DataFrame()

def normalize_columns(save_df, import_df):
    all_cols = list(dict.fromkeys(list(save_df.columns) + list(import_df.columns)))

    for col in all_cols:
        if col not in save_df.columns:
            save_df[col] = ""

        if col not in import_df.columns:
            import_df[col] = ""

    return (save_df[all_cols].fillna(""), import_df[all_cols].fillna(""))