"""SERVICING OS 6.59: invoice warranty fields and safe invoice-print enrichment.

No warranties are invented. An authorized user may enter per-item warranties.
Printing is read-only. Any warranty edit is subject to native ERPNext permission,
submitted-document and audit validations.
"""
import frappe
from frappe.utils import add_days, cint, getdate
from servicing_os.api.invoice_delivery_657 import get_branded_invoice

FIELDS = {
    "custom_sos_warranty_type": ("Select", "Warranty Type", "\nShop Warranty\nManufacturer Warranty\nNo Warranty"),
    "custom_sos_warranty_period_days": ("Int", "Warranty Period (Days)", None),
    "custom_sos_warranty_start_date": ("Date", "Warranty Start Date", None),
    "custom_sos_warranty_expiry_date": ("Date", "Warranty Expiry Date", None),
    "custom_sos_warranty_terms": ("Small Text", "Warranty Terms / Coverage", None),
}
ALLOWED = ("Sales Invoice", "POS Invoice")


def _child_meta(doctype):
    if doctype not in ALLOWED:
        frappe.throw("Unsupported invoice type.")
    child = doctype + " Item"
    if not frappe.db.exists("DocType", child):
        frappe.throw("Invoice line DocType is missing: " + child)
    return child, frappe.get_meta(child)


def _details(row, child_meta):
    def get(field):
        return row.get(field) if child_meta.has_field(field) else None
    source = str(get("custom_sos_warranty_type") or "").strip()
    days = max(0, cint(get("custom_sos_warranty_period_days") or 0))
    start = str(get("custom_sos_warranty_start_date") or "")
    expiry = str(get("custom_sos_warranty_expiry_date") or "")
    terms = str(get("custom_sos_warranty_terms") or "").strip()
    return {
        "row_name": row.name,
        "warranty_type": source,
        "warranty_period_days": days,
        "warranty_start_date": start,
        "warranty_expiry_date": expiry,
        "warranty_terms": terms,
        "warranty_recorded": bool(source or days or expiry or terms),
    }


@frappe.whitelist(methods=["GET"])
def _sos671_get_invoice_with_warranty_original(invoice_name=None, doctype="Sales Invoice"):
    base = get_branded_invoice(invoice_name=invoice_name, doctype=doctype)
    child, meta = _child_meta(doctype)
    inv = frappe.get_doc(doctype, invoice_name)
    inv.check_permission("read")
    rows = list(inv.get("items") or [])
    if len(rows) != len(base.get("items") or []):
        frappe.throw("Invoice line data changed. Refresh and try again.")
    for printed, row in zip(base["items"], rows):
        printed.update(_details(row, meta))
    return base


def _date_or_none(value, label):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return getdate(value)
    except (ValueError, TypeError):
        frappe.throw(label + " must be a valid date.")


@frappe.whitelist(methods=["POST"])
def update_invoice_warranty(data=None):
    if frappe.session.user == "Guest":
        frappe.throw("Login required to update warranty.", frappe.PermissionError)
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if not isinstance(data, dict):
        frappe.throw("Warranty form data is required.")
    name = str(data.get("invoice_name") or "").strip()
    doctype = str(data.get("doctype") or "Sales Invoice").strip()
    row_name = str(data.get("item_row_name") or "").strip()
    if not name or not row_name or len(name) > 140 or len(row_name) > 140:
        frappe.throw("Select a valid invoice line.")
    _child, meta = _child_meta(doctype)
    if any(not meta.has_field(field) for field in FIELDS):
        frappe.throw("Warranty fields are not installed. Run setup_warranty_fields first.")
    inv = frappe.get_doc(doctype, name)
    inv.check_permission("write")
    if inv.docstatus == 2:
        frappe.throw("Cancelled invoices cannot be edited.")
    # Reuse 6.57's read and company scoping validation.
    get_branded_invoice(invoice_name=name, doctype=doctype)
    matching = [r for r in inv.get("items") or [] if r.name == row_name]
    if len(matching) != 1:
        frappe.throw("Invoice item not found on this invoice.")
    row = matching[0]
    source = str(data.get("warranty_type") or "").strip()
    if source not in ("", "Shop Warranty", "Manufacturer Warranty", "No Warranty"):
        frappe.throw("Invalid warranty type.")
    try:
        raw_days = data.get("warranty_period_days") or 0
        if isinstance(raw_days, bool) or str(raw_days).strip() != str(int(raw_days)):
            raise ValueError
        days = int(raw_days)
    except (ValueError, TypeError):
        frappe.throw("Warranty period must be a whole number of days.")
    if days < 0 or days > 36500:
        frappe.throw("Warranty period must be between 0 and 36500 days.")
    if source == "No Warranty" and days:
        frappe.throw("No Warranty cannot have a positive warranty duration.")
    start = _date_or_none(data.get("warranty_start_date"), "Start date")
    expiry = _date_or_none(data.get("warranty_expiry_date"), "Expiry date")
    if not start and days > 0:
        start = getdate(inv.posting_date)
    if not expiry and start and days > 0:
        expiry = add_days(start, days)
    if start and expiry and expiry < start:
        frappe.throw("Warranty expiry cannot precede the warranty start date.")
    if source == "No Warranty" and (start or expiry):
        frappe.throw("No Warranty cannot have a start or expiry date.")
    terms = str(data.get("warranty_terms") or "").strip()
    if len(terms) > 1500:
        frappe.throw("Warranty terms must be 1500 characters or fewer.")
    row.set("custom_sos_warranty_type", source)
    row.set("custom_sos_warranty_period_days", days)
    row.set("custom_sos_warranty_start_date", start)
    row.set("custom_sos_warranty_expiry_date", expiry)
    row.set("custom_sos_warranty_terms", terms)
    # Native Frappe save enforces write and allow_on_submit behavior.
    # Do not bypass it with frappe.db.set_value(ignore_permissions=True).
    inv.save()
    return {"success": True, "invoice": inv.name,
            "item_row_name": row.name, "warranty": _details(row, meta)}


def setup_warranty_fields():
    """Install warranty fields from the Bench console."""
    result = ensure_warranty_fields()
    frappe.db.commit()
    return result


def ensure_warranty_fields():
    """Synchronize warranty fields inside the caller's migration transaction."""
    if frappe.session.user != "Administrator" and not frappe.has_permission("Custom Field", "create"):
        frappe.throw("System Manager permissions required to install warranty fields.", frappe.PermissionError)
    installed = []
    for doctype in ALLOWED:
        child, meta = _child_meta(doctype)
        anchor = "rate" if meta.has_field("rate") else "item_code"
        for fieldname, (fieldtype, label, options) in FIELDS.items():
            if frappe.get_meta(child).has_field(fieldname):
                existing = frappe.get_meta(child).get_field(fieldname)
                if existing.fieldtype != fieldtype:
                    frappe.throw("Existing warranty field has incompatible type: " + child + "." + fieldname)
                anchor = fieldname
                continue
            values = {"doctype": "Custom Field", "dt": child, "fieldname": fieldname,
                      "fieldtype": fieldtype, "label": label, "insert_after": anchor,
                      "allow_on_submit": 1, "read_only": 0,
                      "description": "Recorded warranty for this individual sold item; do not assume coverage."}
            if options is not None:
                values["options"] = options
            frappe.get_doc(values).insert()
            installed.append(child + "." + fieldname)
            frappe.clear_cache(doctype=child)
            anchor = fieldname
        if any(not frappe.db.has_column(child, fieldname) for fieldname in FIELDS):
            frappe.db.updatedb(child)
        if any(not frappe.db.has_column(child, fieldname) for fieldname in FIELDS):
            frappe.throw("Warranty columns did not synchronize for " + child)
    return {"created": installed, "message": "Warranty entry fields are available. Existing invoices unchanged."}


# SERVICING_OS_671 — preserve invoice-line warranty, provide an explicit
# *current* Item Master fallback for older invoices without warranty snapshots.
_get_invoice_with_warranty_before_671 = _sos671_get_invoice_with_warranty_original

@frappe.whitelist(methods=['GET'])
def get_invoice_with_warranty(invoice_name=None, doctype='Sales Invoice'):
    base = _get_invoice_with_warranty_before_671(invoice_name=invoice_name, doctype=doctype)
    # Previous reader already validates company and invoice read permissions.
    if not frappe.has_permission('Item', 'read'):
        return base
    unrecorded = [r for r in base.get('items', []) if not r.get('warranty_recorded') and r.get('item_code')]
    if not unrecorded:
        return base
    from servicing_os.api.item_warranty_671 import _item_periods
    codes = {r['item_code'] for r in unrecorded}
    periods = _item_periods(codes)
    for row in unrecorded:
        days = periods.get(row['item_code'], 0)
        if not days:
            continue
        row['warranty_type'] = 'Current Item Master reference'
        row['warranty_period_days'] = days
        row['warranty_start_date'] = ''
        row['warranty_expiry_date'] = ''
        row['warranty_terms'] = ('Reference only: this Item Master period is current; '
                                 'the original sale warranty was not recorded.')
        row['warranty_recorded'] = True
    return base
