"""Classify Sales Invoices for reporting without changing ledger postings."""
import frappe
from frappe.utils import cint

from servicing_os.revenue_streams import (
    REPORT_STREAM_FIELD,
    SOURCE_FIELDS,
    STREAM_FIELD,
    STREAMS,
    invoice_source_stream,
)


def classification_fields(meta):
    return [field for field in (STREAM_FIELD, REPORT_STREAM_FIELD, "return_against", *SOURCE_FIELDS)
            if meta.has_field(field)]


def can_label():
    return (frappe.session.user == "Administrator"
            or bool({"Accounts Manager", "System Manager"}.intersection(frappe.get_roles()))) and frappe.has_permission(
        "Sales Invoice", "write"
    )


def _direct_stream(row):
    recorded = row.get(STREAM_FIELD)
    if recorded in STREAMS:
        return recorded, "recorded"
    detected = invoice_source_stream(row)
    if detected:
        return detected, "historical"
    label = row.get(REPORT_STREAM_FIELD)
    if label in STREAMS:
        return label, "manual"
    return "Unclassified", "unclassified"


def classifications(rows, company, meta):
    """Return each authorized row's reporting stream and how it was identified."""
    result = {row["name"]: _direct_stream(row) for row in rows}
    returns = [row for row in rows if cint(row.get("is_return")) and row.get("return_against")
               and result[row["name"]][1] != "recorded"]
    if not returns:
        return result

    names = sorted({row["return_against"] for row in returns})
    fields = ["name", *classification_fields(meta)]
    sources = {}
    for offset in range(0, len(names), 250):
        batch = names[offset:offset + 250]
        # The original invoice must pass the same company and read-permission constraints.
        originals = frappe.get_list(
            "Sales Invoice", filters={"company": company, "name": ["in", batch]},
            fields=fields, limit_page_length=len(batch),
        )
        sources.update((row["name"], _direct_stream(row)) for row in originals)
    for row in returns:
        original_stream, basis = sources.get(row["return_against"], ("Unclassified", "unclassified"))
        if basis != "unclassified":
            result[row["name"]] = original_stream, "historical"
    return result
