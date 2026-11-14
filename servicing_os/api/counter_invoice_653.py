"""SERVICING OS 6.53 — service invoice creation, line and overall discounts.

All write actions create DRAFT Sales Invoices only; no submission, stock or GL posting.
ERPNext enforces its native account, tax, customer and document validations.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import frappe
from frappe.utils import nowdate

LINK_FIELD = "custom_service_job"
TWOPLACES = Decimal("0.01")


def _current_user():
    if frappe.session.user == "Guest":
        frappe.throw("Please sign in to SERVICING OS.", frappe.PermissionError)


def _number(value, label, *, allow_zero=False, maximum=Decimal("100000000")):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        frappe.throw("Enter a valid " + label)
    if not result.is_finite() or result > maximum or result < 0 or (not allow_zero and result == 0):
        frappe.throw(label + " is out of range")
    if result.as_tuple().exponent < -2:
        frappe.throw(label + " supports at most 2 decimal places")
    return result


def _valid_service_job(job_name):
    _current_user()
    name = str(job_name or "").strip()
    if not name or len(name) > 140:
        frappe.throw("Select a saved Service Job.")
    doc = frappe.get_doc("Service Job", name)
    doc.check_permission("read")
    if not doc.customer or not frappe.db.exists("Customer", doc.customer):
        frappe.throw("This Service Job has no linked Customer.")
    shop = frappe.get_doc("Servicing Shop", doc.shop)
    shop.check_permission("read")
    if not shop.company or not frappe.db.exists("Company", shop.company) or not shop.is_active:
        frappe.throw("Service Job shop/company is not configured or active.")
    return doc, shop


@frappe.whitelist(methods=["GET"])
def get_counter_invoice_setup():
    """List customer-linked jobs and sellable, non-stock service items."""
    _current_user()
    for doctype, perm in (("Sales Invoice", "create"), ("Service Job", "read"), ("Item", "read")):
        if not frappe.has_permission(doctype, perm):
            frappe.throw(doctype + " " + perm + " permission required", frappe.PermissionError)
    jobs = frappe.get_list(
        "Service Job", fields=["name", "customer", "customer_name", "status", "shop"],
        order_by="creation desc", limit_page_length=200,
    )
    items = frappe.get_list(
        "Item", filters={"disabled": 0, "is_sales_item": 1, "is_stock_item": 0},
        fields=["name", "item_name", "stock_uom"], order_by="name asc", limit_page_length=500,
    )
    return {"jobs": [dict(j) for j in jobs], "items": [dict(i) for i in items], "draft_only": True}


@frappe.whitelist(methods=["POST"])
def create_counter_invoice_draft(job_name=None, items=None, remarks=None,
                                 discount_mode="none", discount_value=0):
    """Explicitly create one native draft Sales Invoice with ERPNext discounts."""
    _current_user()
    if not frappe.has_permission("Sales Invoice", "create"):
        frappe.throw("Sales Invoice create permission required", frappe.PermissionError)
    if not frappe.has_permission("Item", "read"):
        frappe.throw("Item read permission required", frappe.PermissionError)
    if not frappe.get_meta("Sales Invoice").has_field(LINK_FIELD):
        frappe.throw("Sales Invoice custom_service_job link is missing. Restore the repair billing setup first.")

    job, shop = _valid_service_job(job_name)
    # Lock parent to serialize concurrent invoice attempts against one job.
    frappe.db.sql("SELECT name FROM `tabService Job` WHERE name=%s FOR UPDATE", (job.name,))
    existing = frappe.db.exists("Sales Invoice", {LINK_FIELD: job.name, "docstatus": ["<", 2]})
    if existing:
        frappe.throw("An existing draft or submitted invoice already belongs to this job: " + str(existing))

    if isinstance(items, str):
        try:
            items = frappe.parse_json(items)
        except Exception:
            frappe.throw("Invalid invoice lines")
    if not isinstance(items, list) or not 1 <= len(items) <= 30:
        frappe.throw("Include 1–30 invoice lines")

    rows = []
    subtotal = Decimal("0")
    for position, entry in enumerate(items, 1):
        if not isinstance(entry, dict):
            frappe.throw("Invalid row " + str(position))
        code = str(entry.get("item_code") or "").strip()
        if not code or len(code) > 140:
            frappe.throw("Select a valid service Item for row " + str(position))
        if not frappe.has_permission("Item", "read", code):
            frappe.throw("Item read permission required", frappe.PermissionError)
        item = frappe.db.get_value(
            "Item", code, ["name", "disabled", "is_sales_item", "is_stock_item"], as_dict=True,
        )
        if not item or item.disabled or not item.is_sales_item or item.is_stock_item:
            frappe.throw("Row " + str(position) + " must use an active non-stock service Item")
        qty = _number(entry.get("qty"), "Quantity", maximum=Decimal("10000"))
        price = _number(entry.get("rate"), "Rate", allow_zero=True)
        line_pct = _number(entry.get("discount_percentage") or 0, "Line discount %",
                           allow_zero=True, maximum=Decimal("100"))
        line_discount = (price * line_pct / Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        unit_rate = max(Decimal("0"), price - line_discount)
        subtotal += (unit_rate * qty).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        rows.append({"item_code": item.name, "qty": float(qty),
                     "price_list_rate": float(price), "discount_percentage": float(line_pct),
                     "discount_amount": float(line_discount), "rate": float(unit_rate)})
    if subtotal <= 0:
        frappe.throw("Invoice subtotal must be greater than zero after line discounts")

    mode = str(discount_mode or "none").strip().lower()
    if mode not in ("none", "percent", "amount"):
        frappe.throw("Invalid overall discount mode")
    overall = _number(discount_value or 0, "Overall discount", allow_zero=True)
    if mode == "none" and overall != 0:
        frappe.throw("Set discount mode before entering a discount")
    if mode == "percent" and overall > 100:
        frappe.throw("Overall discount percentage must be 0–100")
    if mode == "amount" and overall >= subtotal:
        frappe.throw("Fixed discount must be less than pre-tax subtotal")
    if mode == "percent" and overall == 100:
        frappe.throw("The final invoice amount must be positive")

    company = shop.company
    currency = frappe.db.get_value("Company", company, "default_currency")
    if not currency:
        frappe.throw("Company currency is not configured")
    invoice_fields = {
        "doctype": "Sales Invoice", "company": company, "customer": job.customer,
        "currency": currency, "posting_date": nowdate(), "due_date": nowdate(),
        "remarks": str(remarks or "").strip()[:500] or "Service Job " + job.name,
        LINK_FIELD: job.name, "items": rows,
    }
    if mode != "none" and overall > 0:
        invoice_fields["apply_discount_on"] = "Net Total"
        if mode == "percent":
            invoice_fields["additional_discount_percentage"] = float(overall)
        else:
            invoice_fields["discount_amount"] = float(overall)

    invoice = frappe.get_doc(invoice_fields)
    invoice.insert()  # Native ERPNext validations, pricing, taxes and permissions
    if invoice.docstatus != 0 or invoice.get(LINK_FIELD) != job.name:
        frappe.throw("Draft invoice verification failed; no invoice submitted")
    return {
        "success": True, "invoice": invoice.name, "service_job": job.name,
        "customer": job.customer, "company": company, "currency": invoice.currency,
        "net_total": invoice.net_total, "discount_amount": invoice.discount_amount,
        "grand_total": invoice.grand_total, "docstatus": 0, "submitted": False,
        "message": "Draft saved. Review and submit through the authorized billing process.",
    }


@frappe.whitelist(methods=["GET"])
def get_counter_billing_overview(limit=60):
    _current_user()
    if not frappe.has_permission("Sales Invoice", "read"):
        frappe.throw("Sales Invoice read permission required", frappe.PermissionError)
    if not frappe.get_meta("Sales Invoice").has_field(LINK_FIELD):
        frappe.throw("Sales Invoice custom_service_job link missing")
    try:
        limit = max(1, min(int(limit), 150))
    except (ValueError, TypeError):
        limit = 60
    inv = frappe.get_list(
        "Sales Invoice", filters={"docstatus": ["<", 2], LINK_FIELD: ["is", "set"]},
        fields=["name", "posting_date", "customer", "company", "currency", "status", "docstatus",
                "grand_total", "outstanding_amount", "discount_amount", LINK_FIELD],
        order_by="creation desc", limit_page_length=limit,
    )
    return {"invoices": [dict(i) for i in inv]}


@frappe.whitelist(methods=["GET"])
def get_counter_invoice_detail(invoice_name=None):
    _current_user()
    name = str(invoice_name or "").strip()
    if not name or len(name) > 140:
        frappe.throw("Choose an invoice")
    inv = frappe.get_doc("Sales Invoice", name)
    inv.check_permission("read")
    if not inv.get(LINK_FIELD):
        frappe.throw("This is not a service invoice")
    return {
        "name": inv.name, "company": inv.company, "customer": inv.customer,
        "service_job": inv.get(LINK_FIELD), "posting_date": str(inv.posting_date),
        "status": inv.status, "docstatus": inv.docstatus, "currency": inv.currency,
        "net_total": inv.net_total, "discount_amount": inv.discount_amount,
        "grand_total": inv.grand_total, "outstanding_amount": inv.outstanding_amount,
        "items": [{"item_code": row.item_code, "item_name": row.item_name,
                   "qty": row.qty, "rate": row.rate, "amount": row.amount,
                   "discount_percentage": row.discount_percentage} for row in inv.items],
    }
