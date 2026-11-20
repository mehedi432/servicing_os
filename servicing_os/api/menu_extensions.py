"""SERVICING OS 6.21–6.23: Customers, used-laptop stock intake, staff settings.

All actions use standard Frappe / ERPNext documents. No parallel ledger.
"""
import hashlib
import re
from decimal import Decimal, InvalidOperation

import frappe
from frappe.utils import flt, nowdate
from servicing_os.api.site_company_706 import current_company, current_currency, used_laptop_warehouse

USED_GROUP = "Used Laptops"
ROLE = "Service Technician"


def _require(doctype, action="read", docname=None):
    if not frappe.has_permission(doctype, ptype=action, doc=docname):
        frappe.throw(f"You need {action} permission for {doctype}.", frappe.PermissionError)


def _manager():
    u = frappe.session.user
    return u == "Administrator" or "System Manager" in frappe.get_roles(u)


def _admin():
    if not _manager():
        frappe.throw("Only System Managers can manage shop access.", frappe.PermissionError)


def _safe_money(value):
    try:
        dec = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        frappe.throw("Enter a valid purchase cost in BDT.")
    if not dec.is_finite() or not 0 < dec <= Decimal("100000000"):
        frappe.throw("Purchase cost must be greater than zero.")
    return float(dec.quantize(Decimal("0.01")))


def _check_warehouse():
    w = frappe.db.get_value(
        "Warehouse", used_laptop_warehouse(),
        ["company", "is_group", "disabled"], as_dict=True,
    )
    if not w or w.company != current_company() or w.is_group or w.disabled:
        frappe.throw("The configured used-laptop warehouse must be an active leaf warehouse for this company.")


def setup_used_laptops():
    """Install leaf Item Group only; no Items or accounting entries."""
    if not frappe.db.exists("Company", current_company()):
        frappe.throw("Shop company not found.")
    _check_warehouse()
    if not frappe.db.exists("Item Group", "All Item Groups"):
        frappe.throw("All Item Groups is missing.")
    if frappe.db.exists("Item Group", USED_GROUP):
        if frappe.db.get_value("Item Group", USED_GROUP, "is_group"):
            frappe.throw("Used Laptops exists as a parent group, expected a leaf.")
        return {"group": USED_GROUP, "created": False}
    doc = frappe.get_doc({
        "doctype": "Item Group", "item_group_name": USED_GROUP,
        "parent_item_group": "All Item Groups", "is_group": 0,
    })
    doc.insert(ignore_permissions=True)
    return {"group": USED_GROUP, "created": True}


@frappe.whitelist(methods=["GET"])
def search_customer_cards(search=""):
    _require("Customer")
    from servicing_os.api.counter_customers import search_customers
    return search_customers(search=search)


@frappe.whitelist(methods=["GET"])
def get_customer_card(customer):
    _require("Customer", docname=customer)
    doc = frappe.get_doc("Customer", customer)
    if doc.disabled:
        frappe.throw("Customer is disabled.")
    result = {
        "customer": {"name": doc.name, "customer_name": doc.customer_name,
                     "mobile": doc.get("mobile_no") or ""},
        "jobs": [], "invoices": [], "job_count": 0, "invoice_count": 0,
        "outstanding_bdt": None,
    }
    if frappe.has_permission("Service Job", ptype="read"):
        result["jobs"] = [dict(x) for x in frappe.get_list(
            "Service Job", filters={"customer": customer},
            fields=["name", "status", "device_type", "brand", "device_model",
                    "received_date", "technician"],
            order_by="received_date desc", limit_page_length=60)]
        result["job_count"] = len(result["jobs"])
    if frappe.has_permission("Sales Invoice", ptype="read"):
        invs = frappe.get_list(
            "Sales Invoice", filters={"customer": customer, "docstatus": ["in", [0, 1]]},
            fields=["name", "posting_date", "docstatus", "grand_total", "outstanding_amount",
                    "currency", "status"], order_by="posting_date desc",
            limit_page_length=100,
        )
        result["invoices"] = [dict(x) for x in invs]
        result["invoice_count"] = len(invs)
        result["outstanding_bdt"] = float(sum(
            Decimal(str(x.outstanding_amount or 0)) for x in invs
            if x.docstatus == 1 and x.currency == current_currency()
        ))
    return result


@frappe.whitelist(methods=["GET"])
def get_laptop_hub(search=""):
    _require("Item")
    _check_warehouse()
    query = str(search or "").strip()[:100]
    filters = {"item_group": USED_GROUP, "disabled": 0}
    opts = {"filters": filters,
            "fields": ["name", "item_name", "has_serial_no", "is_stock_item", "stock_uom"],
            "order_by": "modified desc", "limit_page_length": 150}
    if query:
        escaped = query.replace("%", "\\%").replace("_", "\\_")
        opts["or_filters"] = [["Item", "name", "like", "%" + escaped + "%"],
                              ["Item", "item_name", "like", "%" + escaped + "%"]]
    items = [dict(x) for x in frappe.get_list("Item", **opts)]
    for item in items:
        actual = frappe.db.get_value(
            "Bin", {"warehouse": used_laptop_warehouse(), "item_code": item["name"]},
            "actual_qty",
        )
        item["actual_qty"] = flt(actual)
    receipts = []
    if frappe.has_permission("Purchase Receipt", "read"):
        # Only receipts for Item codes in the Used Laptops group.
        receipt_rows = frappe.get_all(
            "Purchase Receipt Item", filters={"item_code": ["in", [x["name"] for x in items]]},
            fields=["parent", "item_code", "serial_no", "rate"],
            limit_page_length=150,
        ) if items else []
        names = list(dict.fromkeys(x.parent for x in receipt_rows))
        allowed = {r.name: r for r in frappe.get_list(
            "Purchase Receipt", filters={"name": ["in", names], "company": current_company()},
            fields=["name", "supplier", "posting_date", "docstatus"],
            limit_page_length=150,
        )} if names else {}
        for r in receipt_rows:
            if r.parent in allowed:
                p = allowed[r.parent]
                receipts.append({"name": r.parent, "supplier": p.supplier,
                                 "posting_date": p.posting_date, "docstatus": p.docstatus,
                                 "item_code": r.item_code, "serial": r.serial_no or "",
                                 "purchase_rate": r.rate if _manager() else None})
    suppliers = []
    if frappe.has_permission("Supplier", "read"):
        suppliers = [dict(x) for x in frappe.get_list(
            "Supplier", filters={"disabled": 0}, fields=["name", "supplier_name"],
            order_by="supplier_name asc", limit_page_length=200)]
    supplier_groups = []
    if frappe.has_permission("Supplier Group", "read"):
        supplier_groups = frappe.get_list("Supplier Group", filters={"is_group": 0},
                                          pluck="name", limit_page_length=200)
    return {"items": items, "receipts": receipts, "suppliers": suppliers,
            "supplier_groups": supplier_groups, "warehouse": used_laptop_warehouse(),
            "can_register": bool(frappe.has_permission("Item", "create") and
                                 frappe.has_permission("Purchase Receipt", "create")),
            "can_submit": bool(frappe.has_permission("Purchase Receipt", "submit")),
            "can_add_supplier": bool(frappe.has_permission("Supplier", "create")),
            "note": "Only submitted stock receipts affect inventory. Drafts do not."}


@frappe.whitelist(methods=["POST"])
def create_supplier_from_counter(name, supplier_group):
    _require("Supplier", "create")
    name = " ".join(str(name or "").strip().split())
    if not 2 <= len(name) <= 120:
        frappe.throw("Enter a supplier name (2–120 characters).")
    if not frappe.db.exists("Supplier Group", supplier_group) or frappe.db.get_value(
        "Supplier Group", supplier_group, "is_group"
    ):
        frappe.throw("Select a valid Supplier Group.")
    if frappe.db.exists("Supplier", name):
        frappe.throw("Supplier already exists. Select the existing record.")
    doc = frappe.get_doc({"doctype": "Supplier", "supplier_name": name,
                          "supplier_group": supplier_group, "supplier_type": "Individual"})
    doc.insert()
    return {"supplier": doc.name, "supplier_name": doc.supplier_name}


@frappe.whitelist(methods=["POST"])
def create_used_laptop_draft(supplier, brand, model, serial, purchase_cost):
    """One unique serialized Item + one *Draft* Purchase Receipt. Never submits."""
    _require("Item", "create")
    _require("Purchase Receipt", "create")
    _check_warehouse()
    if not frappe.db.exists("Item Group", USED_GROUP):
        frappe.throw("Used Laptops group not installed.")
    if not frappe.db.exists("Supplier", supplier) or frappe.db.get_value(
        "Supplier", supplier, "disabled"
    ):
        frappe.throw("Select an enabled Supplier.")
    brand = " ".join(str(brand or "").strip().split())
    model = " ".join(str(model or "").strip().split())
    serial = str(serial or "").strip()
    if not 2 <= len(brand) <= 45 or not 2 <= len(model) <= 90:
        frappe.throw("Enter a valid brand and model.")
    if not 4 <= len(serial) <= 90 or "\n" in serial or "\r" in serial:
        frappe.throw("Enter a genuine device serial number (4–90 characters).")
    if frappe.db.exists("Serial No", serial):
        frappe.throw("This serial number already exists in stock records.")
    key = "UL-" + hashlib.sha256(serial.casefold().encode()).hexdigest()[:16].upper()
    if frappe.db.exists("Item", key):
        frappe.throw("This device was already registered. Check Used Laptops inventory.")
    rate = _safe_money(purchase_cost)
    uom = "Nos"
    if not frappe.db.exists("UOM", uom):
        frappe.throw("UOM 'Nos' is not configured.")
    item = frappe.get_doc({
        "doctype": "Item", "item_code": key,
        "item_name": f"Used {brand} {model} — {serial}"[:140],
        "description": f"Pre-owned device. OEM serial: {serial}",
        "item_group": USED_GROUP, "stock_uom": uom,
        "is_stock_item": 1, "is_sales_item": 1, "is_purchase_item": 1,
        "has_serial_no": 1, "disabled": 0,
    })
    item.insert()
    row = {
        "item_code": item.name, "qty": 1, "rate": rate, "uom": uom,
        "stock_uom": uom, "conversion_factor": 1,
        "warehouse": used_laptop_warehouse(), "serial_no": serial,
    }
    if frappe.get_meta("Purchase Receipt Item").has_field("use_serial_batch_fields"):
        row["use_serial_batch_fields"] = 1
    receipt = frappe.get_doc({
        "doctype": "Purchase Receipt", "company": current_company(), "supplier": supplier,
        "posting_date": nowdate(), "set_warehouse": used_laptop_warehouse(),
        "items": [row],
    })
    receipt.insert()
    return {"item_code": item.name, "purchase_receipt": receipt.name,
            "docstatus": receipt.docstatus, "stock_posted": False,
            "message": "Draft saved. Review and explicitly Receive into Stock."}


@frappe.whitelist(methods=["POST"])
def submit_used_laptop_receipt(receipt_name):
    """Explicit stock-affecting action. Standard PR submission remains authoritative."""
    _require("Purchase Receipt", "submit")
    doc = frappe.get_doc("Purchase Receipt", receipt_name)
    doc.check_permission("submit")
    if doc.docstatus != 0 or doc.company != current_company():
        frappe.throw("Only an company Draft Purchase Receipt can be received.")
    if len(doc.items) != 1 or doc.items[0].qty != 1:
        frappe.throw("Expected exactly one used laptop on this receipt.")
    row = doc.items[0]
    if row.warehouse != used_laptop_warehouse():
        frappe.throw("Receipt must use the Used Laptops warehouse.")
    item = frappe.db.get_value("Item", row.item_code,
                               ["item_group", "has_serial_no"], as_dict=True)
    if not item or item.item_group != USED_GROUP or not item.has_serial_no:
        frappe.throw("Receipt Item is not a serialized used laptop.")
    if not row.serial_no and not row.serial_and_batch_bundle:
        frappe.throw("Missing serial number or Serial/Batch Bundle. No stock was posted.")
    doc.submit()
    return {"purchase_receipt": doc.name, "docstatus": doc.docstatus,
            "stock_posted": True,
            "message": "Receipt submitted. Inventory and valuation are posted by the stock engine."}


@frappe.whitelist(methods=["GET"])
def get_shop_access_settings():
    _admin()
    _require("User")
    shops = []
    if frappe.has_permission("Servicing Shop", "read"):
        shops = [dict(x) for x in frappe.get_list(
            "Servicing Shop", fields=["name", "shop_name", "company", "currency",
                                      "retail_warehouse", "used_laptop_warehouse",
                                      "spare_parts_warehouse", "is_active"],
            limit_page_length=10)]
    users = [dict(x) for x in frappe.get_list(
        "User", filters={"enabled": 1, "user_type": "System User"},
        fields=["name", "full_name"], order_by="full_name asc",
        limit_page_length=200)]
    techs = set(frappe.get_all("Has Role", filters={"parenttype": "User", "role": ROLE},
                               pluck="parent", limit_page_length=1000))
    for u in users:
        u["technician"] = u["name"] in techs
    return {"shops": shops, "users": users,
            "can_manage_roles": bool(frappe.has_permission("User", ptype="write")),
            "company": current_company(), "role": ROLE,
            "info": "Changes here affect technician access only; stock/payment rules remain unchanged."}


@frappe.whitelist(methods=["POST"])
def set_service_technician_role(user_id, enabled):
    _admin()
    _require("User", "write", user_id)
    if not frappe.db.exists("Role", ROLE):
        frappe.throw("Service Technician role is not configured.")
    if user_id in {"Administrator", "Guest"}:
        frappe.throw("Administrator/Guest role assignments cannot be changed here.")
    doc = frappe.get_doc("User", user_id)
    doc.check_permission("write")
    if not doc.enabled or doc.user_type != "System User":
        frappe.throw("Only enabled System Users can be assigned as technicians.")
    assigned = str(enabled).lower() in {"1", "true", "yes"}
    had = any(r.role == ROLE for r in doc.roles)
    if assigned != had:
        if assigned:
            doc.append("roles", {"role": ROLE})
        else:
            for row in list(doc.roles):
                if row.role == ROLE:
                    doc.remove(row)
        doc.save()
    return {"user": doc.name, "technician": assigned, "changed": had != assigned}
