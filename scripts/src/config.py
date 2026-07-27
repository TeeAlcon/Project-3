from pathlib import Path

REPORT_DIR = Path("Drawback Report")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_DIR = Path("Summary Report")
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

AES_FILE = REPORT_DIR / "aes.csv"
GTS_FILE = REPORT_DIR / "gts_sli.csv"
SLI_MAP_FILE = REPORT_DIR / "invoice_sli.csv"
SEA_EXPORT_FILE = REPORT_DIR / "sea_export.csv"
DOC_SEARCH_FILE = REPORT_DIR / "doc_search.csv"
AUDIT_FILE = REPORT_DIR / "audit.csv"
EXPORT_DEC_FILE = REPORT_DIR / "export_dec.csv"
MASTER_SUMMARY_FILE = SUMMARY_DIR / "master_list_summary.csv"
MASTER_DATA_FILE = SUMMARY_DIR / "master_list_data.csv"
DOC_FAIL_FILE = SUMMARY_DIR / "document_fail.csv"


ID_COLS = {   
    AES_FILE: "ITN",
    GTS_FILE: "Shipper's ref num",
    SLI_MAP_FILE: "ITN",
    SEA_EXPORT_FILE: "ITN",
    DOC_SEARCH_FILE: "ITN",
    AUDIT_FILE: "ITN",
    EXPORT_DEC_FILE: "Number"
}

REQUIRED_COLS_FOR_CONFIG = {
    AES_FILE: {"ITN", "Shipment Reference Number", "Commodity Line Value", "Quantity 1"},
    GTS_FILE: {"Shipper's ref num", "Item - Value (USD)","Item - Quantity Schedule B Unit(s)"},
    SLI_MAP_FILE: {"ITN", "Invoice type", "Invoice number"},
    SEA_EXPORT_FILE: {"ITN", "Container Number"},
    DOC_SEARCH_FILE: {"ITN", "Total PDF count", "SLI file count", "AVL file count", "Packing-List file count", "AWB file count", "SWB file count"},
    AUDIT_FILE: {"ITN", "Value Diff", "Qty Diff"},
    EXPORT_DEC_FILE: {"Number"}
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
        "path": AUDIT_FILE,
        "id_col": "ITN"
    }

}

HIERARCHIAL_REPORT = {
    "export_dec": { 
        "title": "Export Dec",
        "path": EXPORT_DEC_FILE,
        "id_col": "Number"
    }
}

ALL_REPORTS = {
    **REPORTS, 
    **HIERARCHIAL_REPORT}