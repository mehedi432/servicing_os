"""SERVICING OS 6.40: overview and direct repair billing (Frappe v15)."""
import json
import re

import frappe
from frappe import _
from frappe.utils import flt, nowdate


LABOUR_ITEM = "SERVICING-LABOUR"
JOB_INVOICE_FIELD = "custom_servicing_invoice"
INVOICE_JOB_FIELD = "custom_servicing_job"


def _authenticated():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please sign in to SERVICING OS"), frappe.PermissionError)


def _shop():
    _authenticated()
    rows = frappe.get_list("Servicing Shop", filters={"is_active": 1},
                           fields=["name", "company"], limit_page_length=1)
    if not rows:
        frappe.throw(_("No accessible active Servicing Shop found. Check shop permissions and setup."))
    return rows[0]


def _job(job_name, permission="read"):
    _authenticated()
    if not job_name or not frappe.db.exists("Service Job", job_name):
        frappe.throw(_("Service Job not found"), frappe.DoesNotExistError)
    doc = frappe.get_doc("Service Job", job_name)
    doc.check_permission(permission)
    if doc.shop != _shop().name:
        frappe.throw(_("Service Job belongs to a different shop"), frappe.PermissionError)
    return doc


def _fields(doctype, names):
    meta = frappe.get_meta(doctype)
    return [name for name in names if name == "name" or meta.has_field(name)]


def _parts_from_job(job):
    """Read existing consumed/used part child tables, without stock posting."""
    results = []
    meta = frappe.get_meta("Service Job")
    for tbl in meta.get_table_fields():
        title = " ".join([tbl.fieldname or "", tbl.label or "", tbl.options or ""]).lower()
        if not any(x in title for x in ("consum", "used", "spare", "part", "material", "component")):
            continue
        cm = frappe.get_meta(tbl.options)
        names = {f.fieldname for f in cm.fields}
        code = next((f for f in ("item_code", "item", "spare_part", "part_item", "product", "part") if f in names), None)
        quantity = next((f for f in ("qty", "quantity", "consumed_qty", "used_qty") if f in names), None)
        if not code or not quantity:
            continue
        rate = next((f for f in ("selling_rate", "sales_rate", "rate", "unit_price", "price", "amount_per_unit") if f in names), None)
        for entry in job.get(tbl.fieldname) or []:
            item_code = str(entry.get(code) or "").strip()
            qty = flt(entry.get(quantity) or 0)
            if item_code and qty > 0 and frappe.db.exists("Item", item_code):
                results.append({"item_code": item_code, "qty": qty,
                                "rate": flt(entry.get(rate)) if rate else 0,
                                "source": tbl.label or tbl.fieldname})
    if results:
        return results
    # Fallback for sites that consume parts via a submitted Material Issue Stock Entry
    # with a Link/Data field explicitly referencing this Service Job.
    se_meta = frappe.get_meta("Stock Entry")
    link = next((f for f in ("service_job", "custom_service_job", "repair_job", "custom_repair_job") if se_meta.has_field(f)), None)
    if not link:
        return results
    entries = frappe.get_list("Stock Entry", filters={link: job.name, "docstatus": 1,
                     "purpose": "Material Issue"}, fields=["name"], limit_page_length=100)
    for se in entries:
        doc = frappe.get_doc("Stock Entry", se.name)
        doc.check_permission("read")
        for row in doc.items:
            if row.item_code and flt(row.qty) > 0:
                results.append({"item_code": row.item_code, "qty": flt(row.qty),
                                "rate": 0, "source": "Posted Material Issue"})
    return results


def _existing_invoice(job):
    if frappe.get_meta("Service Job").has_field(JOB_INVOICE_FIELD):
        linked = job.get(JOB_INVOICE_FIELD)
        if linked and frappe.db.exists("Sales Invoice", linked):
            docstatus = frappe.db.get_value("Sales Invoice", linked, "docstatus")
            if docstatus != 2:
                return linked
    if frappe.get_meta("Sales Invoice").has_field(INVOICE_JOB_FIELD):
        found = frappe.get_list("Sales Invoice", filters={INVOICE_JOB_FIELD: job.name,
                                "docstatus": ["<", 2]}, fields=["name"],
                                limit_page_length=1)
        return found[0].name if found else None
    return None


@frappe.whitelist()
def overview():
    shop = _shop()
    fields = _fields("Service Job", ["name", "status", "customer", "customer_name", "received_date",
                    "device_type", "brand", "device_model", "serial_number", "reported_problem", JOB_INVOICE_FIELD])
    jobs = frappe.get_list("Service Job", filters={"shop": shop.name},
                           fields=fields, order_by="modified desc", limit_page_length=300)
    def status_of(j):
        return str(j.get("status") or "").lower()
    def match(j, words):
        return any(w in status_of(j) for w in words)
    counts = {"total": len(jobs), "new": sum(match(j, ("received", "new", "open", "pending")) for j in jobs),
              "repairing": sum(match(j, ("progress", "diagnos", "repair", "working")) for j in jobs),
              "ready": sum(match(j, ("ready", "complete")) for j in jobs),
              "delivered": sum(match(j, ("deliver", "closed")) for j in jobs),
              "today": sum(str(j.get("received_date") or "").startswith(nowdate()) for j in jobs)}
    # Counts represent the visible 300 most recently changed jobs; don't mislabel as full history.
    total = frappe.get_list("Service Job", filters={"shop": shop.name},
                            fields=["count(name) as total"], limit_page_length=1)
    if total:
        counts["total"] = int(total[0].get("total") or len(jobs))
    return {"shop": shop.name, "company": shop.company, "counts": counts,
            "jobs": [dict(row) for row in jobs], "sample_limited": len(jobs) == 300}


@frappe.whitelist()
def job_bill_preview(job_name):
    job = _job(job_name)
    existing = _existing_invoice(job)
    labour_rate = next((flt(job.get(field)) for field in
                        ("labour_charge", "labor_charge", "service_charge", "repair_charge")
                        if frappe.get_meta("Service Job").has_field(field)), 0)
    parts = _parts_from_job(job)
    # Price is deliberately zero when no selling price has been recorded.
    # Users must approve the prices rather than silently using valuation cost.
    for p in parts:
        if not p["rate"]:
            p["rate"] = flt(frappe.db.get_value("Item", p["item_code"], "standard_rate") or 0)
    return {"job_name": job.name, "customer": job.customer,
            "customer_name": job.get("customer_name"), "labour_item": LABOUR_ITEM,
            "labour_amount": labour_rate, "parts": parts, "existing_invoice": existing,
            "notice": "Already-consumed parts are billed without deducting stock again."}


@frappe.whitelist(methods=["POST"])
def create_job_invoice(job_name, labour_amount=0, parts=None, submit_invoice=0):
    """Create ONE draft Sales Invoice; no repair-status or delivery-stage prerequisite.

    Stock posting is intentionally disabled because parts are already consumed.
    Any unposted parts must be issued through the shop's stock workflow first.
    """
    job = _job(job_name, "write")
    if not frappe.has_permission("Sales Invoice", "create"):
        frappe.throw(_("You need Sales Invoice Create permission."), frappe.PermissionError)
    if not frappe.get_meta("Sales Invoice").has_field(INVOICE_JOB_FIELD):
        frappe.throw(_("Setup incomplete: run setup_schema before billing."))
    submit_invoice = int(submit_invoice or 0)
    # Serialize billing per job so two counter operators cannot invoice it twice.
    frappe.db.sql("SELECT name FROM `tabService Job` WHERE name=%s FOR UPDATE", job.name)
    job.reload()
    existing = _existing_invoice(job)
    if existing:
        inv_existing = frappe.get_doc("Sales Invoice", existing)
        inv_existing.check_permission("read")
        if submit_invoice and inv_existing.docstatus == 0:
            inv_existing.check_permission("submit")
            inv_existing.submit()
        return {"invoice": existing, "already_exists": True,
                "status": "Submitted" if inv_existing.docstatus == 1 else "Draft"}
    if isinstance(parts, str):
        try:
            parts = json.loads(parts)
        except ValueError:
            frappe.throw(_("Invalid parts list"))
    if parts is None:
        parts = _parts_from_job(job)
    if not isinstance(parts, list) or len(parts) > 100:
        frappe.throw(_("Parts must be a list with at most 100 rows"))
    labour = flt(labour_amount)
    if labour < 0:
        frappe.throw(_("Labour charge cannot be negative"))
    valid_parts = []
    for entry in parts:
        if not isinstance(entry, dict):
            frappe.throw(_("Invalid part row"))
        code = str(entry.get("item_code") or "").strip()
        qty, rate = flt(entry.get("qty")), flt(entry.get("rate"))
        if not code or qty <= 0 or rate < 0 or not frappe.db.exists("Item", code):
            frappe.throw(_("Invalid item, quantity or selling rate: {0}").format(code))
        item = frappe.get_doc("Item", code)
        if not item.is_sales_item:
            frappe.throw(_("Item {0} is not enabled for selling").format(code))
        valid_parts.append({"item_code": code, "qty": qty, "rate": rate})
    if not valid_parts and labour <= 0:
        frappe.throw(_("Add a labour charge or consumed part before billing."))
    if labour and not frappe.db.exists("Item", LABOUR_ITEM):
        frappe.throw(_("Missing non-stock Item SERVICING-LABOUR. Run setup_schema."))

    shop = _shop()
    if not job.customer or not frappe.db.exists("Customer", job.customer):
        frappe.throw(_("Service Job must have a valid ERPNext Customer"))
    inv = frappe.new_doc("Sales Invoice")
    inv.company = shop.company
    inv.customer = job.customer
    inv.due_date = nowdate()
    inv.update_stock = 0
    inv.set(INVOICE_JOB_FIELD, job.name)
    inv.remarks = "SERVICING OS Service Job: " + job.name
    if labour:
        inv.append("items", {"item_code": LABOUR_ITEM, "qty": 1, "rate": labour,
                             "description": "Service / repair labour for " + job.name})
    for line in valid_parts:
        inv.append("items", line)
    # Leave ERPNext validation and permissions intact. Status steps on Service Job
    # are not required; the invoice may be saved as draft or submitted directly.
    if hasattr(inv, "set_missing_values"):
        inv.set_missing_values()
    if hasattr(inv, "calculate_taxes_and_totals"):
        inv.calculate_taxes_and_totals()
    inv.insert()
    if submit_invoice:
        inv.check_permission("submit")
        inv.submit()
    if frappe.get_meta("Service Job").has_field(JOB_INVOICE_FIELD):
        job.db_set(JOB_INVOICE_FIELD, inv.name, update_modified=False)
    return {"invoice": inv.name, "already_exists": False,
            "grand_total": inv.grand_total,
            "status": "Submitted" if inv.docstatus == 1 else "Draft"}


@frappe.whitelist()
def part_search(query=""):
    _authenticated()
    query = str(query or "").strip()
    if len(query) < 2:
        return []
    filters = {"disabled": 0, "is_sales_item": 1}
    return frappe.get_list("Item", filters=filters,
                or_filters=[["item_code", "like", "%" + query + "%"],
                            ["item_name", "like", "%" + query + "%"]],
                fields=["name", "item_name", "standard_rate", "is_stock_item"],
                limit_page_length=15)


def setup_schema():
    """Run using `bench --site SITE execute servicing_os.api.counter40.setup_schema`."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
        frappe.throw(_("System Manager required"), frappe.PermissionError)
    create_custom_fields({
        "Service Job": [{"fieldname": JOB_INVOICE_FIELD, "label": "Servicing Invoice",
                         "fieldtype": "Link", "options": "Sales Invoice", "read_only": 1,
                         "insert_after": "status"}],
        "Sales Invoice": [{"fieldname": INVOICE_JOB_FIELD, "label": "Servicing Job",
                           "fieldtype": "Link", "options": "Service Job",
                           "insert_after": "customer"}],
    }, update=True)
    if not frappe.db.exists("Item", LABOUR_ITEM):
        group = ("Services" if frappe.db.exists("Item Group", "Services") else
                 frappe.db.get_value("Item Group", {"is_group": 0}, "name"))
        if not group:
            frappe.throw(_("Create at least one leaf Item Group (preferably Services) first."))
        frappe.get_doc({"doctype": "Item", "item_code": LABOUR_ITEM,
                        "item_name": "Computer Repair / Service Labour", "item_group": group,
                        "stock_uom": "Nos", "is_stock_item": 0,
                        "is_sales_item": 1, "is_purchase_item": 0}).insert()
    frappe.db.commit()
    return {"result": "Service Invoice schema and non-stock labour item are ready"}
