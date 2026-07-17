from pathlib import Path

REPORT_DIR = Path("Drawback Report")

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

AES_FILE = REPORT_DIR / "AES Report.csv"
GTS_FILE = REPORT_DIR / "GTS SLI.csv"
SLI_MAP_FILE = REPORT_DIR / "SLI Map.csv"
SEA_EXPORT_FILE = REPORT_DIR / "Sea Export Date.csv"
DOC_SEARCH_FILE = REPORT_DIR / "Doc Search.csv"
AUDIT_DOC_FILE = REPORT_DIR / "Audit Doc.csv"
MASTER_LIST_FILE = REPORT_DIR / "Master List.csv"
EXPORT_DEC_FILE = REPORT_DIR / "Export Dec.csv"

ID_COLS = {   
    AES_FILE: "ITN",
    GTS_FILE: "Shipper's ref num",
    SLI_MAP_FILE: "ITN",
    SEA_EXPORT_FILE: "ITN",
    DOC_SEARCH_FILE: "ITN",
    AUDIT_DOC_FILE: "ITN",
    EXPORT_DEC_FILE: "Number",
}

REPORTS = {
    "aes": {
        "title": "AES Report",
        "path": AES_FILE,
        "id_col": "ITN"
    },

    "gts": {
        "title": "GTS-SLI",
        "path": GTS_FILE,
        "id_col": "Shipper's ref num"
    },

    "sli_map": {
        "title": "SLI Map",
        "path": SLI_MAP_FILE,
        "id_col": "ITN"
    },

    "sea_export": {
        "title": "Sea Export",
        "path": SEA_EXPORT_FILE,
        "id_col": "ITN"
    },

    "doc_search": {
        "title": "Doc Search",
        "path": DOC_SEARCH_FILE,
        "id_col": "ITN"
    },

    "audit_doc": {
        "title": "Audit Doc",
        "path": AUDIT_DOC_FILE,
        "id_col": "ITN"
    },

    "export_dec": {
        "title": "Export Dec",
        "path": EXPORT_DEC_FILE,
        "id_col": "Number"
    }
}