"""SERVICING OS Purchase Orders for ERPNext v15.

Scopes requests to the active shop company and uses native permissions and validation.
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
RECEIPT_BLOCKED_STATUSES = ("Closed", "Completed", "Cancelled", "On Hold")


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
def _purchase_order(name, permission="read", *, for_update=False):
    _require_login()
    name = str(name or "").strip()
    if not name or len(name) > 200:
        frappe.throw("Select a valid Purchase Order")
    po = frappe.get_doc("Purchase Order", name, for_update=True) if for_update else frappe.get_doc("Purchase Order", name)
    if po.company != _company():
        frappe.throw("Purchase Order is not available for this shop", frappe.PermissionError)
    po.check_permission("read")
    if permission != "read":
        po.check_permission(permission)
    return po


def _has_purchase_order_workflow():
    return bool(frappe.db.exists("Workflow", {"document_type": "Purchase Order", "is_active": 1}))


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
    "can_delete": bool(frappe.has_permission("Purchase Order", "delete")),
    "can_submit": bool(frappe.has_permission("Purchase Order", "submit")) and not _has_purchase_order_workflow()}


@frappe.whitelist(methods=["GET"])
def get_purchase_order_record(name=None):
    return _order_details(_purchase_order(name))


def _order_details(po):
    items = po.get("items") or []
    first = items[0] if items else {}
    draft = int(po.docstatus) == 0
    uses_workflow = draft and _has_purchase_order_workflow()
    return {
        "name": po.name, "docstatus": int(po.docstatus), "status": po.get("status") or ("Draft" if draft else "Submitted"),
        "modified": str(po.modified), "supplier": po.supplier, "supplier_name": po.get("supplier_name") or po.supplier,
        "warehouse": po.get("set_warehouse") or first.get("warehouse") or "",
        "transaction_date": str(po.get("transaction_date") or ""),
        "schedule_date": str(po.get("schedule_date") or first.get("schedule_date") or ""),
        "company": po.company, "currency": po.currency, "remarks": po.get("remarks") or "",
        "net_total": float(po.get("net_total") or 0), "grand_total": float(po.get("grand_total") or 0),
        "can_edit": draft and bool(frappe.has_permission("Purchase Order", "write", doc=po)),
        "can_delete": draft and bool(frappe.has_permission("Purchase Order", "delete", doc=po)),
        "can_submit": draft and not uses_workflow and bool(frappe.has_permission("Purchase Order", "submit", doc=po)),
        "uses_workflow": uses_workflow,
        "can_receive": _can_receive(po) and bool(frappe.has_permission("Purchase Receipt", "create")),
        "can_view_receipts": not draft and bool(frappe.has_permission("Purchase Receipt", "read")),
        "items": [
            {"name": row.get("name"), "item_code": row.get("item_code"), "item_name": row.get("item_name"),
             "qty": float(row.get("qty") or 0), "received_qty": float(row.get("received_qty") or 0),
             "rate": float(row.get("rate") or 0),
             "amount": float(row.get("amount") or 0),
             "uom": row.get("uom"), "warehouse": row.get("warehouse"),
             "schedule_date": str(row.get("schedule_date") or "")}
            for row in items
        ],
    }


@frappe.whitelist(methods=["POST"])
def submit_purchase_order(data=None):
    payload = frappe.parse_json(data) if isinstance(data, str) else data
    if not isinstance(payload, dict):
        frappe.throw("Select and review a draft Purchase Order.")
    po = _purchase_order(payload.get("name"))
    po.check_permission("submit")
    locked = frappe.db.get_value("Purchase Order", po.name, ["modified", "docstatus"], for_update=True)
    if locked and int(locked[1]) == 1:
        return {"name": po.name, "docstatus": 1, "already_submitted": True}
    expected = str(payload.get("expected_modified") or "")
    if (not locked or int(locked[1]) != 0 or int(po.docstatus) != 0
            or str(locked[0]) != expected or str(po.modified) != expected):
        frappe.throw("This draft changed after review. Reopen the Purchase Order before submitting.")
    if _has_purchase_order_workflow():
        frappe.throw("This Purchase Order uses a workflow. Open it in ERPNext to complete the approval steps.")
    po.submit()
    if int(po.docstatus) != 1:
        frappe.throw("The Purchase Order did not reach Submitted status.")
    return {"name": po.name, "docstatus": 1, "already_submitted": False}


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


def _search_term(search):
    return str(search or "").strip()[:140].replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def _receipt_page(page):
    try:
        return max(1, min(int(page or 1), 10000))
    except (ValueError, TypeError):
        return 1


def _receipt_item_filters(**filters):
    return {"parenttype": "Purchase Receipt", "parentfield": "items", **filters}


@frappe.whitelist(methods=["GET"])
def list_supplier_receipts(search="", page=1, purchase_order=None):
    """List permission-filtered ERPNext purchase receipts for the active shop."""
    _require_login()
    doctype = "Purchase Receipt"
    if not frappe.has_permission(doctype, "read"):
        frappe.throw("Purchase Receipt read permission is required.", frappe.PermissionError)
    page = _receipt_page(page)
    term = _search_term(search)
    match = [[field, "like", f"%{term}%"] for field in ("name", "supplier", "supplier_name")] if term else None
    size = 20
    filters = {"company": _company()}
    if purchase_order:
        po = _purchase_order(purchase_order)
        names = frappe.get_all("Purchase Receipt Item", filters=_receipt_item_filters(purchase_order=po.name),
                               pluck="parent", distinct=True)
        if not names:
            return {"rows": [], "has_next": False, "can_create": bool(frappe.has_permission(doctype, "create"))}
        filters["name"] = ["in", names]
    rows = frappe.get_list(doctype, filters=filters, or_filters=match,
                           fields=["name", "supplier", "supplier_name", "posting_date", "status", "is_return", "set_warehouse"],
                           order_by="posting_date desc, name desc", limit_start=(page - 1) * size,
                           limit_page_length=size + 1)
    if rows and frappe.has_permission("Purchase Order", "read"):
        links = frappe.get_all("Purchase Receipt Item",
                               filters=_receipt_item_filters(parent=["in", [r["name"] for r in rows[:size]]],
                                                             purchase_order=["is", "set"]),
                               fields=["parent", "purchase_order"], distinct=True)
        if links:
            order_names = sorted({row.purchase_order for row in links})
            readable = frappe.get_list("Purchase Order", filters={"company": filters["company"],
                                     "name": ["in", order_names]}, pluck="name", limit_page_length=len(order_names))
            by_receipt = {}
            for link in links:
                if link.purchase_order in readable:
                    by_receipt.setdefault(link.parent, []).append(link.purchase_order)
            for row in rows[:size]:
                row["purchase_orders"] = sorted(by_receipt.get(row["name"], []))
    return {"rows": rows[:size], "has_next": len(rows) > size,
            "can_create": bool(frappe.has_permission(doctype, "create"))}


@frappe.whitelist(methods=["GET"])
def list_purchase_orders_to_receive(search="", page=1):
    _require_login()
    if not frappe.has_permission("Purchase Order", "read"):
        return {"rows": [], "has_next": False, "can_read": False}
    term = _search_term(search)
    match = [[field, "like", f"%{term}%"] for field in ("name", "supplier", "supplier_name")] if term else None
    size = 20
    rows = frappe.get_list("Purchase Order", filters={
        "company": _company(), "docstatus": 1, "status": ["not in", RECEIPT_BLOCKED_STATUSES],
        "per_received": ["<", 100],
    }, or_filters=match,
        fields=["name", "supplier", "supplier_name", "schedule_date", "per_received"],
        order_by="schedule_date asc, name desc", limit_start=(_receipt_page(page) - 1) * size,
        limit_page_length=size + 1)
    return {"rows": rows[:size], "has_next": len(rows) > size, "can_read": True}


def _can_receive(po):
    return int(po.docstatus) == 1 and po.get("status") not in RECEIPT_BLOCKED_STATUSES and (
        float(po.get("per_received") or 0) < 100 or bool(po.get("has_unit_price_items")))


def _receiving_lines(po):
    result = []
    for row in po.get("items") or []:
        remaining = Decimal(str(row.get("qty") or 0)) - Decimal(str(row.get("received_qty") or 0))
        if remaining <= 0 or int(row.get("delivered_by_supplier") or 0):
            continue
        result.append({
            "name": row.get("name"), "item_code": row.get("item_code"), "item_name": row.get("item_name"),
            "uom": row.get("uom"), "warehouse": row.get("warehouse"), "remaining": float(remaining),
        })
    return result


def _receiving_warehouses(company, name=None):
    if not frappe.has_permission("Warehouse", "read"):
        frappe.throw("Warehouse read permission is required.", frappe.PermissionError)
    filters = {"company": company, "is_group": 0, "disabled": 0}
    if name:
        filters["name"] = name
    return frappe.get_list("Warehouse", filters=filters, fields=["name", "warehouse_name"],
                           order_by="warehouse_name asc", limit_page_length=500)


def _receive_order(name, *, for_update=False):
    po = _purchase_order(name, for_update=for_update)
    if not frappe.has_permission("Purchase Receipt", "create"):
        frappe.throw("Purchase Receipt create permission is required.", frappe.PermissionError)
    if not _can_receive(po):
        frappe.throw("Only open, submitted Purchase Orders with goods remaining can be received.")
    return po


@frappe.whitelist(methods=["GET"])
def get_purchase_order_receiving(name=None):
    po = _receive_order(name)
    needs_native = bool(po.get("is_subcontracted") or po.get("has_unit_price_items"))
    has_draft = bool(frappe.db.get_value(
        "Purchase Receipt Item", _receipt_item_filters(purchase_order=po.name, docstatus=0), "parent"))
    items = _receiving_lines(po) if not needs_native else []
    for line in items:
        line["requires_details"] = _requires_receipt_details(line["item_code"])
    return {"items": items, "needs_native": needs_native, "has_draft": has_draft, "modified": str(po.modified),
            "warehouses": _receiving_warehouses(po.company) if items else [],
            "can_submit": bool(frappe.has_permission("Purchase Receipt", "submit"))
            and not frappe.db.exists("Workflow", {"document_type": "Purchase Receipt", "is_active": 1})}


@frappe.whitelist(methods=["POST"])
def receive_purchase_order(data=None):
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

    payload = frappe.parse_json(data) if isinstance(data, str) else data
    if not isinstance(payload, dict) or payload.get("action") not in ("receive", "draft"):
        frappe.throw("Select how to save this Purchase Receipt.")
    po = _receive_order(payload.get("name"), for_update=True)
    if po.get("is_subcontracted") or po.get("has_unit_price_items"):
        frappe.throw("Open the Purchase Order in ERPNext to receive this order.")
    if str(po.modified) != str(payload.get("expected_modified") or ""):
        frappe.throw("This order changed after review. Reopen it and check the quantities.")
    warehouse = str(payload.get("warehouse") or "").strip()
    if not warehouse or not _receiving_warehouses(po.company, warehouse):
        frappe.throw("Select an active, accessible warehouse in this company.")
    if frappe.db.get_value("Purchase Receipt Item", _receipt_item_filters(purchase_order=po.name, docstatus=0),
                           "parent", for_update=True):
        frappe.throw("A draft receipt is already linked to this order. Open Purchase Receipts to review it.")
    requested = payload.get("items")
    available = {line["name"]: line for line in _receiving_lines(po)}
    if not isinstance(requested, list) or not 1 <= len(requested) <= len(available):
        frappe.throw("Select one or more items with quantity remaining. Refresh if the order was recently received.")
    quantities = {}
    post_stock = payload["action"] == "receive"
    if post_stock and frappe.db.exists("Workflow", {"document_type": "Purchase Receipt", "is_active": 1}):
        frappe.throw("This receipt requires approval. Save a draft and finish the workflow in ERPNext.")
    for entry in requested:
        key = str(entry.get("name") or "") if isinstance(entry, dict) else ""
        if key not in available or key in quantities:
            frappe.throw("Select unique items with quantity remaining on this order.")
        line = available[key]
        remaining = Decimal(str(line["remaining"]))
        if _decimal(entry.get("remaining"), "Reviewed quantity") != remaining:
            frappe.throw("The remaining quantity changed. Refresh the receiving form before continuing.")
        qty = _decimal(entry.get("qty"), "Receipt quantity")
        if qty > remaining:
            frappe.throw("Receipt quantity exceeds the outstanding quantity for " + line["item_code"])
        if post_stock and _requires_receipt_details(line["item_code"]):
            frappe.throw("This item requires serial, batch, or inspection details. Save a draft and complete it in ERPNext.")
        quantities[key] = qty

    receipt = make_purchase_receipt(po.name)
    mapped = {row.purchase_order_item: row for row in receipt.items}
    if not quantities.keys() <= mapped.keys():
        frappe.throw("ERPNext could not map all selected items. Refresh the receiving form before continuing.")
    receipt.set("items", [row for row in receipt.items if row.purchase_order_item in quantities])
    receipt.set_warehouse = warehouse
    receipt.apply_putaway_rule = 0
    for row in receipt.items:
        quantity = quantities[row.purchase_order_item]
        if quantity > Decimal(str(row.qty)):
            frappe.throw("The remaining quantity changed. Refresh the receiving form before continuing.")
        row.qty = row.received_qty = float(quantity)
        row.stock_qty = row.received_stock_qty = row.qty * float(row.conversion_factor or 1)
        row.warehouse = warehouse
    if post_stock:
        receipt.check_permission("submit")
    receipt.insert()
    if post_stock:
        receipt.submit()
    if int(receipt.docstatus) != int(post_stock):
        frappe.throw("The Purchase Receipt did not reach the requested status.")
    return {"name": receipt.name, "docstatus": int(receipt.docstatus), "warehouse": warehouse}


def _requires_receipt_details(item_code):
    fields = ["has_serial_no", "has_batch_no", "inspection_required_before_purchase"]
    flags = frappe.get_cached_value("Item", item_code, fields) or ()
    return any(int(value or 0) for value in flags)
