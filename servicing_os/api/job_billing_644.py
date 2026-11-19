"""SERVICING OS — direct Sales Invoice from a Service Job (Frappe/ERPNext v15).

The repair finalizer controls submission and any approved stock issue.
This module never uses ignore_permissions.
"""
import json
from collections import OrderedDict

import frappe
from frappe.utils import flt, nowdate

from servicing_os.api.service_invoice_661 import active_sale_invoice_names, linked_job

LINK_FIELD = "custom_servicing_job"
STOCK_LINK_FIELDS = ("service_job", "custom_service_job")
KNOWN_PART_TABLE_NAMES = (
    "consumed_items", "consumed_parts", "parts_used", "used_parts",
    "spare_parts_used", "service_parts", "used_spare_parts",
    "parts_consumed", "service_consumables",
)


def _clean(v):
    return str(v or "").strip()


def _read_job(name):
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to SERVICING OS", frappe.PermissionError)
    name = _clean(name)
    if not name or not frappe.db.exists("Service Job", name):
        frappe.throw("Service Job not found")
    job = frappe.get_doc("Service Job", name)
    if not frappe.has_permission("Service Job", "read", doc=job):
        frappe.throw("No permission to read this Service Job", frappe.PermissionError)
    return job


def _company(job):
    shop = _clean(job.get("shop"))
    if not shop:
        frappe.throw("Service Job has no shop; please configure the shop")
    sdoc = frappe.get_doc("Servicing Shop", shop)
    if not frappe.has_permission("Servicing Shop", "read", doc=sdoc):
        frappe.throw("No permission to use this shop", frappe.PermissionError)
    company = _clean(sdoc.get("company"))
    if not company or not frappe.db.exists("Company", company):
        frappe.throw("Servicing Shop has no valid Company")
    return company


def _previous_invoice(job):
    names = active_sale_invoice_names(job.name, _company(job))
    if len(names) > 1:
        frappe.throw("Multiple active invoices found for this Service Job.")
    if names:
        invoice = frappe.get_doc("Sales Invoice", names[0])
        invoice.check_permission("read")
        return {"name": invoice.name, "docstatus": invoice.docstatus, "grand_total": invoice.grand_total}
    for field in ("sales_invoice", "invoice", "repair_invoice"):
        name = _clean(job.get(field))
        if name and frappe.db.exists("Sales Invoice", name):
            inv = frappe.get_doc("Sales Invoice", name)
            if inv.docstatus < 2 and inv.company == _company(job) and inv.customer == job.customer:
                inv.check_permission("read")
                return {"name": inv.name, "docstatus": inv.docstatus, "grand_total": inv.grand_total}
    return None


def _part_rows_from_job(job):
    rows = []
    for field in frappe.get_meta("Service Job").fields:
        if field.fieldtype != "Table" or field.fieldname not in KNOWN_PART_TABLE_NAMES:
            continue
        for row in (job.get(field.fieldname) or []):
            code = _clean(row.get("item_code") or row.get("item"))
            qty = flt(row.get("consumed_qty") or row.get("used_qty") or row.get("qty") or row.get("quantity"))
            if not code or not frappe.db.exists("Item", code) or qty <= 0:
                continue
            rate = flt(row.get("selling_rate") or row.get("selling_price") or row.get("rate") or 0)
            rows.append({"item_code": code, "item_name": frappe.db.get_value("Item", code, "item_name") or code,
                         "qty": qty, "rate": rate, "source": "Recorded consumed parts"})
    return rows


def _part_rows_from_stock_entry(job, company):
    # Only a submitted Stock Entry with an explicit link to THIS job is accepted.
    meta = frappe.get_meta("Stock Entry")
    link_field = next((f for f in STOCK_LINK_FIELDS if meta.has_field(f)
                       and meta.get_field(f).fieldtype == "Link"
                       and meta.get_field(f).options == "Service Job"), None)
    if not link_field:
        return []
    entries = frappe.get_list("Stock Entry", filters={link_field: job.name, "company": company,
                                                     "docstatus": 1, "purpose": "Material Issue"},
                              fields=["name"], limit_page_length=500)
    rows = []
    for entry in entries:
        stock_entry = frappe.get_doc("Stock Entry", entry.name)
        if not frappe.has_permission("Stock Entry", "read", doc=stock_entry):
            continue
        for item in stock_entry.items:
            code = _clean(item.item_code)
            qty = flt(item.qty)
            if code and qty > 0:
                rows.append({"item_code": code,
                             "item_name": frappe.db.get_value("Item", code, "item_name") or code,
                             "qty": qty, "rate": 0,
                             "source": "Stock Entry " + stock_entry.name})
    return rows


def _parts(job, company):
    # Avoid double counting when the same consumption is recorded in the job and a Stock Entry.
    rows = _part_rows_from_job(job)
    if not rows:
        rows = _part_rows_from_stock_entry(job, company)
    merged = OrderedDict()
    for row in rows:
        key = row["item_code"]
        if key in merged:
            merged[key]["qty"] += row["qty"]
            merged[key]["rate"] = max(merged[key]["rate"], row["rate"])
        else:
            merged[key] = row.copy()
    return list(merged.values())


@frappe.whitelist(methods=["GET"])
def search_jobs(q=""):
    if frappe.session.user == "Guest":
        frappe.throw("Please log in", frappe.PermissionError)
    q = _clean(q)[:100]
    filters = {"name": ["like", "%" + q + "%"]} if q else {}
    jobs = frappe.get_list("Service Job", filters=filters, fields=["name", "customer_name", "status"],
                           order_by="modified desc", limit_page_length=20)
    return jobs


@frappe.whitelist(methods=["GET"])
def invoice_preview(service_job):
    job = _read_job(service_job)
    company = _company(job)
    existing = _previous_invoice(job)
    return {
        "job": job.name, "customer": job.get("customer"), "customer_name": job.get("customer_name"),
        "company": company, "status": job.get("status"),
        "currency": frappe.db.get_value("Company", company, "default_currency") or "BDT",
        "estimate": flt(job.get("estimated_cost")), "existing_invoice": existing,
        "parts": _parts(job, company),
        "stock_note": "Items on this invoice are billable only. This invoice will not change stock."
    }


def _invoice_rows(lines, company):
    if not isinstance(lines, list) or not lines or len(lines) > 100:
        frappe.throw("Add at least one invoice line (maximum 100)")
    rows = []
    total = 0
    default_income = frappe.db.get_value("Company", company, "default_income_account")
    company_doc = frappe.get_doc("Company", company)
    default_cost_center = company_doc.get("cost_center") or company_doc.get("default_cost_center")
    for line in lines:
        if not isinstance(line, dict):
            frappe.throw("Invalid invoice row")
        code = _clean(line.get("item_code"))
        name = _clean(line.get("item_name"))
        qty = flt(line.get("qty"))
        rate = flt(line.get("rate"))
        if qty <= 0 or qty > 100000 or rate < 0 or rate > 100000000:
            frappe.throw("Invalid quantity or rate for invoice line")
        if code:
            if not frappe.db.exists("Item", code):
                frappe.throw("Unknown Item: " + code)
            item = frappe.get_doc("Item", code)
            if item.disabled or item.is_sales_item == 0:
                frappe.throw("Item is not enabled for sales: " + code)
            rows.append({"item_code": code, "qty": qty, "rate": rate,
                         "description": _clean(line.get("description")) or name or item.item_name})
        else:
            if not name:
                frappe.throw("Enter a charge description")
            if not default_income:
                frappe.throw("Set Default Income Account in Company settings to bill service charges without an Item Code")
            row = {"item_name": name[:140], "description": name[:140], "qty": qty,
                   "rate": rate, "uom": "Nos", "income_account": default_income}
            if default_cost_center:
                row["cost_center"] = default_cost_center
            rows.append(row)
        total += qty * rate
    if total <= 0:
        frappe.throw("Invoice total must be greater than zero")
    return rows


@frappe.whitelist(methods=["POST"])
def create_invoice(service_job, lines=None, submit=0):
    job = _read_job(service_job)
    if _clean(job.get("status")).lower() in ("cancelled", "canceled"):
        frappe.throw("Cancelled Service Jobs cannot be invoiced")
    company = _company(job)
    customer = _clean(job.get("customer"))
    if not customer or not frappe.db.exists("Customer", customer):
        frappe.throw("A valid Customer must be linked to this Service Job")
    if not frappe.has_permission("Sales Invoice", "create"):
        frappe.throw("Your role cannot create Sales Invoices", frappe.PermissionError)
    should_submit = str(submit).lower() in ("1", "true", "yes")
    if should_submit and not frappe.has_permission("Sales Invoice", "submit"):
        frappe.throw("Your role cannot submit Sales Invoices", frappe.PermissionError)
    if isinstance(lines, str):
        try:
            lines = json.loads(lines)
        except (TypeError, ValueError):
            frappe.throw("Invalid invoice lines")
    rows = _invoice_rows(lines, company)
    # Serialise invoice creation for one Service Job to avoid duplicates from double-clicks.
    frappe.db.sql("SELECT name FROM `tabService Job` WHERE name=%s FOR UPDATE", (job.name,))
    existing = _previous_invoice(job)
    if existing:
        frappe.throw("An active invoice already exists for this job: " + existing["name"])
    meta = frappe.get_meta("Sales Invoice")
    field = "custom_service_job" if meta.has_field("custom_service_job") else LINK_FIELD
    invoice = frappe.get_doc({
        "doctype": "Sales Invoice", "company": company, "customer": customer,
        field: job.name, "posting_date": nowdate(), "due_date": nowdate(),
        "update_stock": 0, "remarks": "SERVICING OS / Service Job " + job.name,
        "items": rows,
    })
    invoice.insert()  # Frappe and ERPNext validation, permissions, tax and accounting defaults.
    if should_submit:
        from servicing_os.api.invoice_review import submit_reviewed_invoice
        submit_reviewed_invoice(invoice.name, str(invoice.modified))
        invoice.reload()
    return {"invoice": invoice.name, "submitted": invoice.docstatus == 1,
            "grand_total": invoice.grand_total, "currency": invoice.currency}


@frappe.whitelist(methods=["POST"])
def submit_existing_invoice(service_job, invoice_name):
    """Submit an already saved draft from SERVICING OS (no ERPNext Desk navigation)."""
    from servicing_os.api.invoice_review import submit_reviewed_invoice

    job = _read_job(service_job)
    invoice = frappe.get_doc("Sales Invoice", _clean(invoice_name))
    invoice.check_permission("read")
    if linked_job(invoice) != job.name:
        frappe.throw("This invoice is not linked to the selected Service Job.")
    submit_reviewed_invoice(invoice.name, str(invoice.modified))
    return {"invoice": invoice.name, "submitted": True,
            "grand_total": invoice.grand_total, "currency": invoice.currency}


def ensure_invoice_link():
    """Run once as Administrator using bench execute; do not call from browser."""
    if frappe.get_meta("Sales Invoice").has_field(LINK_FIELD):
        field = frappe.get_meta("Sales Invoice").get_field(LINK_FIELD)
        if field.fieldtype != "Link" or field.options != "Service Job":
            frappe.throw("Existing custom_servicing_job has incompatible definition")
        return "Sales Invoice link exists"
    doc = frappe.get_doc({
        "doctype": "Custom Field", "dt": "Sales Invoice", "fieldname": LINK_FIELD,
        "label": "Servicing Job", "fieldtype": "Link", "options": "Service Job",
        "insert_after": "customer", "no_copy": 1, "read_only": 1,
    })
    doc.insert()
    frappe.clear_cache(doctype="Sales Invoice")
    frappe.db.commit()
    return "Created Sales Invoice.custom_servicing_job"
