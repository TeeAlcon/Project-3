def highlight_fail_rows(row):
    value_fail = (
        "Value Audit" in row.index
        and row["Value Audit"] == "FAIL"
    ) 
    qty_fail = (
        "Qty Diff" in row.index
        and row["Qty Audit"] == "FAIL"
    )
    audit_fail = (
        "Audit Status" in row.index
        and row["Audit Status"] == "FAIL"
    )
    doc_fail = (
        "Document Status" in row.index
        and row["Document Status"] == "FAIL"
    )
    if value_fail or qty_fail or doc_fail or audit_fail:
        return["background-color: #8B0000"] * len(row)
    return [""] * len(row)