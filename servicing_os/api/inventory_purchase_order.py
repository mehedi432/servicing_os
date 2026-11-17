"""SERVICING OS — safe draft Purchase Order workflow for ERPNext v15.

Scopes every request to the active Servicing Shop company, performs normal Frappe
permission checks, never bypasses ERPNext validations, and never submits orders.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation

import frappe
from frappe.utils import getdate, today

from servicing_os.api.inventory_workspace import _company, _currency, _warehouses, _price_lists

MAX_CATALOG = 2500
MAX_SUPPLIERS = 500
MAX_LINES = 60


def _require_login():
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to SERVICING OS", frappe.PermissionError)


def _permitted_warehouses(company):
    return _warehouses(company)


def _is_enabled_supplier(supplier):
    # Supplier 'disabled' is standard on ERPNext, but check metadata for custom schemas.
    meta = frappe.get_meta("Supplier")
    filters = {"name": supplier}
    if meta.has_field("disabled"):
        filters["disabled"] = 0
    return bool(frappe.get_list("Supplier", filters=filters, fields=["name"], limit_page_length=1))


def _decimal(value, label, allow_zero=False):
    try:
        result = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        frappe.throw(label + " must be a valid number")
    if not result.is_finite() or result < 0 or (not allow_zero and result == 0):
        frappe.throw(label + " must be greater than zero" if not allow_zero else label + " cannot be negative")
    if result > Decimal("100000000"):
        frappe.throw(label + " exceeds allowed limit")
    return result


@frappe.whitelist(methods=["GET"])
def get_purchase_order_context(warehouse=None):
    _require_login()
    company = _company()
    if not frappe.has_permission("Item", "read") or not frappe.has_permission("Warehouse", "read"):
        frappe.throw("Item and Warehouse read access are required", frappe.PermissionError)

    warehouses = _permitted_warehouses(company)
    allowed = {w.name for w in warehouses}
    warehouse = str(warehouse or "").strip()
    if warehouse and warehouse not in allowed:
        frappe.throw("Warehouse is not part of the active shop", frappe.PermissionError)

    supplier_fields = ["name", "supplier_name"]
    if frappe.get_meta("Supplier").has_field("supplier_group"):
        supplier_fields.append("supplier_group")
    supplier_filters = {}
    if frappe.get_meta("Supplier").has_field("disabled"):
        supplier_filters["disabled"] = 0
    suppliers = []
    if frappe.has_permission("Supplier", "read"):
        suppliers = frappe.get_list("Supplier", filters=supplier_filters, fields=supplier_fields,
                                    order_by="supplier_name asc", limit_page_length=MAX_SUPPLIERS + 1)

    item_rows = frappe.get_list("Item", filters={"disabled": 0, "is_stock_item": 1},
                                fields=["name"], order_by="modified desc",
                                limit_page_length=MAX_CATALOG + 1)
    item_codes = [r.name for r in item_rows[:MAX_CATALOG]]
    items_set = set(item_codes)
    stock = {}
    if item_codes and allowed:
        stock_rows = frappe.get_list("Bin", filters={
            "item_code": ["in", item_codes], "warehouse": ["in", list(allowed)]},
            fields=["item_code", "warehouse", "actual_qty", "reserved_qty"],
            limit_page_length=20001)
        if len(stock_rows) > 20000:
            frappe.throw("Too many stock balances. Limit the shop catalog before planning purchases.")
        for bin_row in stock_rows:
            stock[f"{bin_row.item_code}::{bin_row.warehouse}"] = round(
                float(bin_row.actual_qty or 0)-float(bin_row.reserved_qty or 0), 3)

    rules = {}
    if item_codes and allowed:
        for r in frappe.get_all("Item Reorder", filters={"parent": ["in", item_codes],
                                                       "warehouse": ["in", list(allowed)]},
                                fields=["parent", "warehouse", "warehouse_reorder_level", "warehouse_reorder_qty"],
                                limit_page_length=20000):
            if r.parent in items_set:
                rules[f"{r.parent}::{r.warehouse}"] = {
                    "level": float(r.warehouse_reorder_level or 0),
                    "reorder_qty": float(r.warehouse_reorder_qty or 0),
                }

    # Pending Purchase Orders are not assumed to be zero when access is denied.
    pending_visible = bool(frappe.has_permission("Purchase Order", "read"))
    pending = {}
    if pending_visible and item_codes and allowed:
        # Respect Purchase Order record-level user permissions. A bare SQL JOIN
        # would bypass Frappe's user-permission filters for non-Administrator.
        accessible = frappe.get_list("Purchase Order", filters={
            "company": company, "docstatus": 1,
            "status": ["not in", ["Closed", "Completed", "Cancelled", "On Hold"]],
        }, fields=["name"], limit_page_length=5001)
        # A user may have doctype read permission but only see a subset of
        # purchase orders due to user permissions. Avoid incorrect reorder
        # recommendations unless the accessible count matches the company total.
        company_open_count = frappe.db.count("Purchase Order", filters={
            "company": company, "docstatus": 1,
            "status": ["not in", ["Closed", "Completed", "Cancelled", "On Hold"]],
        })
        if len(accessible) > 5000 or len(accessible) != company_open_count:
            pending_visible = False
        elif accessible:
            names = tuple(r.name for r in accessible)
            rows = frappe.db.sql("""
                SELECT poi.item_code, poi.warehouse,
                       SUM(GREATEST(0, (poi.qty - IFNULL(poi.received_qty, 0))
                           * IFNULL(NULLIF(poi.conversion_factor, 0), 1))) AS pending_qty
                FROM `tabPurchase Order Item` poi
                INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
                WHERE po.company = %(company)s AND po.docstatus = 1
                  AND po.name IN %(permitted)s
                  AND poi.item_code IN %(item_codes)s AND poi.warehouse IN %(warehouses)s
                GROUP BY poi.item_code, poi.warehouse
            """, {"company": company, "permitted": names,
                  "item_codes": tuple(item_codes), "warehouses": tuple(allowed)}, as_dict=True)
            for r in rows:
                pending[f"{r.item_code}::{r.warehouse}"] = round(float(r.pending_qty or 0), 3)

    lists = _price_lists(company)
    return {
        "company": company, "currency": _currency(company), "buying_price_list": lists.get("buying"),
        "warehouses": [{"name": w.name, "warehouse_name": w.warehouse_name} for w in warehouses],
        "suppliers": [{"name": r.name, "supplier_name": r.supplier_name or r.name,
                       "supplier_group": r.get("supplier_group") or ""} for r in suppliers[:MAX_SUPPLIERS]],
        "suppliers_truncated": len(suppliers) > MAX_SUPPLIERS,
        "catalog_truncated": len(item_rows) > MAX_CATALOG,
        "stock_by_warehouse": stock,
        "reorder_rules": rules, "pending_orders": pending, "pending_visible": pending_visible,
        "can_create": bool(frappe.has_permission("Purchase Order", "create")),
        "can_edit": bool(frappe.has_permission("Purchase Order", "write")),
        "can_submit": bool(frappe.has_permission("Purchase Order", "submit")),
        "supplier_read": bool(frappe.has_permission("Supplier", "read")),
    }


@frappe.whitelist(methods=["POST"])
def create_purchase_order_draft(data=None):
    """Create a DRAFT only, with ERPNext's normal save validations and permissions."""
    _require_login()
    company = _company()
    if not frappe.has_permission("Purchase Order", "create"):
        frappe.throw("Purchase Order create permission required", frappe.PermissionError)
    payload = frappe.parse_json(data) if isinstance(data, str) else (data or {})
    if not isinstance(payload, dict):
        frappe.throw("Invalid purchase order payload")
    supplier = str(payload.get("supplier") or "").strip()
    if not supplier or not _is_enabled_supplier(supplier):
        frappe.throw("Choose an active, accessible Supplier")

    allowed = {w.name for w in _permitted_warehouses(company)}
    warehouse = str(payload.get("warehouse") or "").strip()
    if not warehouse or warehouse not in allowed:
        frappe.throw("Choose an accessible leaf warehouse for this company")
    delivery = getdate(payload.get("schedule_date") or "1900-01-01")
    if delivery < getdate(today()) or delivery > getdate(today()) + timedelta(days=365 * 2):
        frappe.throw("Required-by date must be today or within the next two years")
    note = str(payload.get("remarks") or "").strip()
    if len(note) > 2000:
        frappe.throw("Remarks exceed 2,000 characters")

    incoming = payload.get("items")
    if not isinstance(incoming, list) or not 1 <= len(incoming) <= MAX_LINES:
        frappe.throw("Add between 1 and 60 purchase order items")
    codes = [str(r.get("item_code") or "").strip() for r in incoming if isinstance(r, dict)]
    if len(codes) != len(incoming) or len(set(codes)) != len(codes):
        frappe.throw("Each purchase order item must have a unique item code")
    permitted_items = frappe.get_list("Item", filters={"name": ["in", codes],
                                                        "disabled": 0, "is_stock_item": 1},
                                      fields=["name", "item_name", "stock_uom"],
                                      limit_page_length=MAX_LINES + 1)
    index = {i.name: i for i in permitted_items}
    if set(codes) != set(index):
        frappe.throw("One or more products are unavailable or not permitted")

    lines = []
    for row in incoming:
        code = str(row.get("item_code") or "").strip()
        qty = _decimal(row.get("qty"), "Quantity for " + code)
        rate = _decimal(row.get("rate"), "Buying rate for " + code)
        lines.append({
            "item_code": code, "item_name": index[code].item_name,
            "qty": float(qty), "uom": index[code].stock_uom,
            "conversion_factor": 1,
            "rate": float(rate), "warehouse": warehouse,
            "schedule_date": str(delivery),
        })

    price_list = _price_lists(company).get("buying")
    doc_data = {
        "doctype": "Purchase Order", "company": company, "supplier": supplier,
        "transaction_date": today(), "schedule_date": str(delivery),
        "set_warehouse": warehouse, "currency": _currency(company),
        "items": lines, "remarks": note,
    }
    if price_list:
        doc_data["buying_price_list"] = price_list
    po = frappe.get_doc(doc_data)
    po.insert()  # no ignore_permissions / no force insert / no submit
    if po.docstatus != 0:
        frappe.throw("Unexpected document state after saving")
    return {"name": po.name, "docstatus": po.docstatus, "company": po.company,
            "supplier": po.supplier, "currency": po.currency,
            "grand_total": float(po.grand_total or 0), "items_count": len(po.items),
            "status": po.status or "Draft"}


# SOS_INV_PO_V54 — list, inspect, update and delete draft Purchase Orders.
# All operations use the active shop's company and normal record permissions.
def _purchase_order(name, permission="read"):
    _require_login()
    name = str(name or "").strip()
    if not name or len(name) > 200:
        frappe.throw("Select a valid Purchase Order")
    po = frappe.get_doc("Purchase Order", name)
    if po.company != _company():
        frappe.throw("Purchase Order is not available for this shop", frappe.PermissionError)
    po.check_permission(permission)
    return po


@frappe.whitelist(methods=["GET"])
def list_purchase_orders(page=0, status="all", search=""):
    _require_login()
    if not frappe.has_permission("Purchase Order", "read"):
        frappe.throw("Purchase Order read permission required", frappe.PermissionError)
    try:
        page = max(0, min(int(page), 200))
    except (ValueError, TypeError):
        page = 0
    status = str(status or "all").lower()
    if status not in ("all", "draft", "submitted"):
        frappe.throw("Invalid order status filter")
    search = str(search or "").strip()
    if len(search) > 120:
        frappe.throw("Search is too long")
    conditions = {"company": _company(), "docstatus": ["in", [0, 1]]}
    if status == "draft":
        conditions["docstatus"] = 0
    elif status == "submitted":
        conditions["docstatus"] = 1
    if search:
        conditions["name"] = ["like", "%"+search+"%"]
    rows = frappe.get_list("Purchase Order",filters=conditions,
        fields=["name","supplier","transaction_date","schedule_date","docstatus","status","grand_total","currency","modified"],
        order_by="modified desc", start=page*40, limit_page_length=41)
    return {"orders":[{
        "name": r.name, "supplier":r.supplier, "transaction_date":str(r.transaction_date or ""),
        "schedule_date":str(r.schedule_date or ""),"docstatus":int(r.docstatus),
        "status":r.status or ("Draft" if int(r.docstatus)==0 else "Submitted"),
        "grand_total":float(r.grand_total or 0),"currency":r.currency or "BDT",
        "modified":str(r.modified or "")
    } for r in rows[:40]], "has_more":len(rows)>40,"page":page,
    "can_create": bool(frappe.has_permission("Purchase Order", "create")),
    "can_edit": bool(frappe.has_permission("Purchase Order", "write")),
    "can_delete": bool(frappe.has_permission("Purchase Order", "delete"))}


@frappe.whitelist(methods=["GET"])
def get_purchase_order_record(name=None):
    po = _purchase_order(name, "read")
    return {
        "name":po.name,"docstatus":int(po.docstatus),"status":po.status or "Draft",
        "supplier":po.supplier,"warehouse":po.set_warehouse or (po.items[0].warehouse if po.items else ""),
        "schedule_date":str(po.schedule_date or (po.items[0].schedule_date if po.items else "")),
        "company":po.company,"currency":po.currency,"remarks":po.remarks or "",
        "grand_total":float(po.grand_total or 0),
        "can_edit":int(po.docstatus)==0 and bool(frappe.has_permission("Purchase Order", "write", doc=po)),
        "can_delete":int(po.docstatus)==0 and bool(frappe.has_permission("Purchase Order", "delete", doc=po)),
        "items":[{"item_code":r.item_code,"item_name":r.item_name,"qty":float(r.qty or 0),
            "rate":float(r.rate or 0),"uom":r.uom,"warehouse":r.warehouse} for r in po.items]
    }


def _validated_changes(payload, company):
    """Validate edited values through the same Item/Supplier/warehouse rules as create."""
    supplier = str(payload.get("supplier") or "").strip()
    if not supplier or not _is_enabled_supplier(supplier):
        frappe.throw("Choose an active and accessible Supplier")
    allowed = {w.name for w in _permitted_warehouses(company)}
    warehouse = str(payload.get("warehouse") or "").strip()
    if not warehouse or warehouse not in allowed:
        frappe.throw("Choose an accessible leaf warehouse for this company")
    delivery = getdate(payload.get("schedule_date") or "1900-01-01")
    if delivery < getdate(today()) or delivery > getdate(today()) + timedelta(days=365*2):
        frappe.throw("Required-by date must be today or within two years")
    remarks = str(payload.get("remarks") or "").strip()
    if len(remarks) > 2000:
        frappe.throw("Remarks exceed 2,000 characters")
    incoming = payload.get("items")
    if not isinstance(incoming,list) or not 1 <= len(incoming) <= MAX_LINES:
        frappe.throw("Add between 1 and 60 products")
    codes = [str(r.get("item_code") or "").strip() for r in incoming if isinstance(r,dict)]
    if len(codes)!=len(incoming) or len(set(codes))!=len(codes):
        frappe.throw("Each item must have a unique valid item code")
    permitted = frappe.get_list("Item", filters={"name":["in",codes],"disabled":0,"is_stock_item":1},
        fields=["name","item_name","stock_uom"],limit_page_length=MAX_LINES+1)
    index={r.name:r for r in permitted}
    if set(codes)!=set(index):
        frappe.throw("Some Items are unavailable or not permitted")
    lines=[]
    for r in incoming:
        code=str(r.get("item_code") or "").strip()
        qty=_decimal(r.get("qty"),"Quantity for "+code)
        rate=_decimal(r.get("rate"),"Buying rate for "+code)
        lines.append({"item_code":code,"item_name":index[code].item_name,"qty":float(qty),
            "uom":index[code].stock_uom,"conversion_factor":1,"rate":float(rate),
            "warehouse":warehouse,"schedule_date":str(delivery)})
    return supplier, warehouse, delivery, remarks, lines


@frappe.whitelist(methods=["POST"])
def update_purchase_order_draft(data=None):
    _require_login()
    payload=frappe.parse_json(data) if isinstance(data,str) else (data or {})
    if not isinstance(payload,dict):
        frappe.throw("Invalid Purchase Order payload")
    po=_purchase_order(payload.get("name"), "write")
    if int(po.docstatus)!=0:
        frappe.throw("Only Draft Purchase Orders can be edited")
    supplier,warehouse,delivery,remarks,lines=_validated_changes(payload,po.company)
    po.supplier=supplier
    po.schedule_date=str(delivery)
    po.set_warehouse=warehouse
    po.remarks=remarks
    po.set("items", lines)
    po.save()  # standard validation, normal permissions, no submission
    return {"name":po.name,"docstatus":int(po.docstatus),"company":po.company,
        "supplier":po.supplier,"currency":po.currency,"grand_total":float(po.grand_total or 0),
        "items_count":len(po.items),"status":po.status or "Draft"}


@frappe.whitelist(methods=["POST"])
def delete_purchase_order_draft(data=None):
    _require_login()
    payload=frappe.parse_json(data) if isinstance(data,str) else (data or {})
    if not isinstance(payload,dict):
        frappe.throw("Invalid deletion request")
    po=_purchase_order(payload.get("name"),"delete")
    if int(po.docstatus)!=0:
        frappe.throw("Submitted or cancelled Purchase Orders cannot be deleted from SERVICING OS")
    frappe.delete_doc("Purchase Order",po.name,ignore_permissions=False)
    return {"deleted":True,"name":po.name}
