"""Supplier warranty records on permission-checked Purchase Receipt lines."""

import re

import frappe
from frappe.utils import add_days, getdate, today

from servicing_os.api.inventory_warranty import _page, _reference, _require, _serials, _term
from servicing_os.api.inventory_workspace import _company
from servicing_os.api.warranty_serials import voucher_serials
from servicing_os.warranty_schema import RECEIPT_FIELDS

RECEIPT = "Purchase Receipt"
LINE = "Purchase Receipt Item"
SIZE = 12
TYPES = ("Supplier Warranty", "Manufacturer Warranty", "No Warranty")
FIELDS = dict(zip(("kind", "starts", "expires", "reference", "terms"), RECEIPT_FIELDS))
FILTERS = ("all", "expiring", "expired", "missing", "active", "none")


def _confirm_schema():
    meta = frappe.get_meta(LINE)
    if any(not meta.has_field(field) for field in RECEIPT_FIELDS):
        frappe.throw("Supplier warranty fields are missing. Run bench migrate for this site.")


def _date(value, label):
    if not value:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        frappe.throw(f"{label} must use YYYY-MM-DD format.")
    try:
        return getdate(value)
    except (TypeError, ValueError):
        frappe.throw(f"{label} is not a valid date.")


def _coverage(row, as_of):
    data = {key: row.get(field) or "" for key, field in FIELDS.items()}
    start, expiry = data["starts"], data["expires"]
    days = (getdate(str(expiry)) - as_of).days if expiry else None
    if data["kind"] == "No Warranty":
        state = "none"
    elif days is None:
        state = "missing"
    elif days < 0:
        state = "expired"
    elif start and getdate(str(start)) > as_of:
        state = "upcoming"
    else:
        state = "expiring" if days <= 30 else "active"
    return {**data, "status": state, "days_remaining": days}


def _line_filters(state, as_of):
    end, start = FIELDS["expires"], FIELDS["starts"]
    if state == "expiring":
        return [[LINE, end, "between", [as_of, add_days(as_of, 30)]]]
    if state == "expired":
        return [[LINE, end, "is", "set"], [LINE, end, "<", as_of]]
    if state == "missing":
        return [[LINE, end, "is", "not set"], [LINE, FIELDS["kind"], "!=", "No Warranty"]]
    if state == "none":
        return [[LINE, FIELDS["kind"], "=", "No Warranty"]]
    if state == "active":
        return [[LINE, end, ">=", as_of]]
    return []


def _query_receipts(company, search, state, page, as_of):
    term = _term(search)
    columns = ("name", "supplier", "supplier_name")
    matches = None
    if term:
        matches = [[table, field, "like", f"%{term}%"] for table, fields in
                   ((RECEIPT, columns), (LINE, ("item_code", "item_name", FIELDS["reference"])))
                   for field in fields]
    line_filters = _line_filters(state, as_of)
    qty_filter = [[LINE, "qty", ">", 0]] if line_filters or term else []
    return frappe.get_list(
        RECEIPT, filters=[[RECEIPT, "company", "=", company], [RECEIPT, "docstatus", "=", 1],
                          [RECEIPT, "is_return", "=", 0], *qty_filter, *line_filters],
        or_filters=matches, fields=[*columns, "posting_date"],
        order_by="posting_date desc, name desc", distinct=True,
        limit_start=(page - 1) * SIZE, limit_page_length=SIZE + 1,
    )


@frappe.whitelist(methods=["GET"])
def list_receipts(search="", state="all", page=1):
    company = _company()
    _require(RECEIPT)
    _confirm_schema()
    if state not in FILTERS:
        frappe.throw("Choose a valid supplier warranty filter.")
    as_of = getdate(today())
    page = _page(page)
    receipts = _query_receipts(company, search, state, page, as_of)
    return {"receipts": receipts[:SIZE], "has_next": len(receipts) > SIZE}


def _receipt(name, action="read"):
    company = _company()
    _require(RECEIPT, action)
    _confirm_schema()
    receipt = frappe.get_doc(RECEIPT, _reference(name, "purchase receipt"))
    receipt.check_permission("read")
    if action != "read":
        receipt.check_permission(action)
    if receipt.company != company or receipt.docstatus != 1 or receipt.get("is_return"):
        frappe.throw("Select a submitted purchase receipt for this shop.")
    return receipt


def _stored_line(row, bundle_serials, as_of):
    return {
        "name": row.name, "item_code": row.item_code, "item_name": row.item_name,
        "quantity": row.qty, "uom": row.uom, "warehouse": row.warehouse,
        "serials": _serials(bundle_serials.get(row.name) or row.get("serial_no")),
        "batch_no": row.get("batch_no") or "",
        **_coverage(row, as_of),
    }


def _stock_by_item(lines):
    warehouses = {line["warehouse"] for line in lines if line["warehouse"]}
    if not warehouses or not frappe.has_permission("Bin", "read"):
        return {}
    items = {line["item_code"] for line in lines}
    bins = frappe.get_list(
        "Bin", filters={"warehouse": ["in", list(warehouses)], "item_code": ["in", list(items)]},
        fields=["item_code", "warehouse", "actual_qty"], limit_page_length=len(items) * len(warehouses),
    )
    return {(row.item_code, row.warehouse): row.actual_qty for row in bins}


@frappe.whitelist(methods=["GET"])
def get_receipt(receipt, state="all", search=""):
    doc = _receipt(receipt)
    if state not in FILTERS:
        frappe.throw("Choose a valid supplier warranty filter.")
    as_of = getdate(today())
    rows = [row for row in doc.items if row.qty > 0]
    serials = voucher_serials(doc, rows)
    lines = [_stored_line(row, serials, as_of) for row in rows]
    if state == "active":
        lines = [line for line in lines if line["status"] in ("active", "expiring", "upcoming")]
    elif state != "all":
        lines = [line for line in lines if line["status"] == state or (
            state == "expiring" and line["status"] == "upcoming" and line["days_remaining"] <= 30
        )]
    term = str(search or "").strip()[:140].casefold()
    receipt_values = (doc.name, doc.supplier, doc.get("supplier_name"))
    if term and not any(term in (value or "").casefold() for value in receipt_values):
        matching = [line for line in lines if any(term in (line[key] or "").casefold()
                                                  for key in ("item_code", "item_name", "reference"))]
        # The database may match accented text that is spelled differently.
        if matching:
            lines = matching
    on_hand = _stock_by_item(lines)
    for line in lines:
        line["sku_on_hand"] = on_hand.get((line["item_code"], line["warehouse"]))
    return {
        "name": doc.name, "supplier": doc.supplier, "supplier_name": doc.get("supplier_name"),
        "posting_date": doc.posting_date, "modified": str(doc.modified), "lines": lines,
        "can_edit": bool(doc.has_permission("write")),
    }


@frappe.whitelist(methods=["POST"])
def save_coverage(receipt, line, modified, kind="", starts="", expires="", reference="", terms=""):
    doc = _receipt(receipt, "write")
    if str(doc.modified) != modified:
        frappe.throw("This receipt changed. Reopen it and try again.")
    row = next((row for row in doc.items if row.name == line and row.qty > 0), None)
    if not row:
        frappe.throw("Select an accepted item line from the receipt.")
    kind = str(kind or "")
    if kind and kind not in TYPES:
        frappe.throw("Choose a valid supplier coverage type.")
    start, expiry = _date(starts, "Start date"), _date(expires, "Expiry date")
    if kind in TYPES[:2] and not expiry:
        frappe.throw("Enter the supplier warranty expiry date.")
    if kind not in TYPES[:2] and (start or expiry):
        frappe.throw("Choose a coverage type before saving warranty dates.")
    if start and expiry and start > expiry:
        frappe.throw("Expiry cannot be earlier than the start date.")
    reference, terms = str(reference or "").strip(), str(terms or "").strip()
    if len(reference) > 140 or len(terms) > 2000:
        frappe.throw("Use up to 140 characters for the reference and 2,000 for terms.")
    values = {"kind": kind, "starts": start, "expires": expiry, "reference": reference, "terms": terms}
    for key, field in FIELDS.items():
        row.set(field, values[key])
    doc.save()
    return {"name": doc.name, "line": row.name}
