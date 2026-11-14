"""SERVICING OS 6.52 — permission-checked service invoice DRAFT workflow.

This does not submit a Sales Invoice, post general ledger entries, or collect
payments. Existing ERPNext validations and document permissions remain active.
"""
from decimal import Decimal, InvalidOperation

import frappe
from frappe.utils import nowdate

LINK_FIELD = "custom_service_job"


def _require_user():
    if frappe.session.user == "Guest":
        frappe.throw("Sign in to create a service invoice.", frappe.PermissionError)


def _number(value, label, allow_zero=False):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        frappe.throw("Enter a valid " + label)
    if not number.is_finite() or (number < 0 if allow_zero else number <= 0):
        frappe.throw(label + " must be " + ("zero or positive" if allow_zero else "positive"))
    if number > Decimal("100000000") or number.as_tuple().exponent < -2:
        frappe.throw(label + " must have at most 2 decimal places and be within allowed limits")
    return number


def _get_valid_job(job_name):
    _require_user()
    job_name = str(job_name or "").strip()
    if not job_name or len(job_name) > 140:
        frappe.throw("Choose a saved Service Job before billing.")
    if not frappe.has_permission("Service Job", "read"):
        frappe.throw("Service Job read permission required.", frappe.PermissionError)
    job = frappe.get_doc("Service Job", job_name)
    job.check_permission("read")
    if not job.customer or not frappe.db.exists("Customer", job.customer):
        frappe.throw("The Service Job must reference an existing Customer.")
    if not job.shop or not frappe.db.exists("Servicing Shop", job.shop):
        frappe.throw("The Service Job has no valid Servicing Shop.")
    shop = frappe.get_doc("Servicing Shop", job.shop)
    if shop.get("is_active") == 0 or not shop.company or not frappe.db.exists("Company", shop.company):
        frappe.throw("The service shop company configuration is not active/valid.")
    return job, shop


@frappe.whitelist(methods=["GET"])
def get_counter_invoice_setup():
    """Show only permitted Service Jobs and non-stock sellable service Items."""
    _require_user()
    if not frappe.has_permission("Sales Invoice", "create"):
        frappe.throw("Sales Invoice create permission required.", frappe.PermissionError)
    if not frappe.has_permission("Service Job", "read"):
        frappe.throw("Service Job read permission required.", frappe.PermissionError)
    if not frappe.has_permission("Item", "read"):
        frappe.throw("Item read permission required.", frappe.PermissionError)
    jobs = frappe.get_list(
        "Service Job", fields=["name", "customer", "customer_name", "status", "shop"],
        order_by="creation desc", limit_page_length=100,
    )
    items = frappe.get_list(
        "Item", filters={"disabled": 0, "is_sales_item": 1, "is_stock_item": 0},
        fields=["name", "item_name", "stock_uom"], order_by="name asc",
        limit_page_length=250,
    )
    return {
        "jobs": [dict(j) for j in jobs],
        "items": [dict(i) for i in items],
        "draft_only": True,
        "note": "A draft is not a tax-issued invoice. Review and submit it through your authorized billing workflow.",
    }


@frappe.whitelist(methods=["POST"])
def create_counter_invoice_draft(job_name=None, items=None, remarks=None):
    """Create ONE draft ERPNext Sales Invoice against a saved Service Job."""
    _require_user()
    if not frappe.has_permission("Sales Invoice", "create"):
        frappe.throw("Sales Invoice create permission required.", frappe.PermissionError)
    job, shop = _get_valid_job(job_name)
    if not frappe.get_meta("Sales Invoice").has_field(LINK_FIELD):
        frappe.throw("Sales Invoice is missing the Service Job link field custom_service_job. Configure the existing repair-billing integration first.")
    duplicate = frappe.db.exists("Sales Invoice", {LINK_FIELD: job.name, "docstatus": ["<", 2]})
    if duplicate:
        frappe.throw("A draft or submitted Sales Invoice already exists for this Service Job. Check billing records before creating another.")
    if isinstance(items, str):
        try:
            items = frappe.parse_json(items)
        except (TypeError, ValueError):
            frappe.throw("Invalid invoice item list.")
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        frappe.throw("Include between 1 and 20 invoice lines.")
    rows = []
    for entry in items:
        if not isinstance(entry, dict):
            frappe.throw("Invalid invoice item row.")
        item_code = str(entry.get("item_code") or "").strip()
        if not item_code or len(item_code) > 140:
            frappe.throw("Select a valid Item Code for every invoice row.")
        if not frappe.has_permission("Item", "read", item_code):
            frappe.throw("Item read permission required.", frappe.PermissionError)
        item = frappe.db.get_value(
            "Item", item_code, ["name", "disabled", "is_sales_item", "is_stock_item"],
            as_dict=True,
        )
        if not item or item.disabled or not item.is_sales_item:
            frappe.throw("Selected item is not enabled for sale.")
        if item.is_stock_item:
            frappe.throw("Stock items require a stock-aware invoice workflow. Use a non-stock service Item here; bill physical parts through the existing authorized billing workflow.")
        qty = _number(entry.get("qty"), "Quantity")
        rate = _number(entry.get("rate"), "Rate", allow_zero=True)
        if qty > Decimal("10000"):
            frappe.throw("Quantity is too large.")
        rows.append({"item_code": item.name, "qty": float(qty), "rate": float(rate)})
    remarks = str(remarks or "").strip()[:500]
    company = shop.company
    default_currency = frappe.db.get_value("Company", company, "default_currency")
    if not default_currency:
        frappe.throw("Company default currency is not configured.")
    doc = frappe.get_doc({
        "doctype": "Sales Invoice",
        "company": company,
        "customer": job.customer,
        "currency": default_currency,
        "due_date": nowdate(),
        "remarks": remarks or "Service Job " + job.name,
        LINK_FIELD: job.name,
        "items": rows,
    })
    doc.insert()  # Applies ERPNext accounting rules and user permissions.
    if doc.docstatus != 0 or doc.get(LINK_FIELD) != job.name:
        frappe.throw("Invoice draft verification failed; nothing has been submitted.")
    return {
        "success": True,
        "invoice": doc.name,
        "service_job": job.name,
        "customer": job.customer,
        "company": company,
        "currency": doc.currency,
        "grand_total": doc.grand_total,
        "docstatus": doc.docstatus,
        "submitted": False,
        "message": "Draft Sales Invoice created. Review and submit using your authorized billing process.",
    }
