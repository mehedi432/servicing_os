"""SERVICING OS | live inventory dashboard and controlled stock adjustments.

Only ERPNext records, never local demo inventory. Designed for Frappe / ERPNext v15.
Frappe permission-aware reads; no ignore_permissions during writes.
"""
import frappe
from frappe.utils import flt

MAX_ITEMS = 2500
MAX_BINS = 15000


def _shop_company():
    if frappe.session.user == "Guest":
        frappe.throw("Please log in", frappe.PermissionError)
    # The shop and its company are explicitly scoped to visible Servicing Shop records.
    shops = frappe.get_list(
        "Servicing Shop",
        filters={"is_active": 1},
        fields=["name", "company"],
        limit_page_length=1,
    )
    if not shops or not shops[0].get("company"):
        frappe.throw("No accessible active Servicing Shop with Company was found")
    return shops[0].company


def _warehouses(company):
    return frappe.get_list(
        "Warehouse", filters={"company": company, "is_group": 0},
        fields=["name", "warehouse_name"],
        order_by="warehouse_name asc", limit_page_length=500,
    )


@frappe.whitelist(methods=["GET"])
def get_inventory(warehouse=None):
    company = _shop_company()
    if not frappe.has_permission("Item", "read"):
        frappe.throw("Item read permission is required", frappe.PermissionError)
    if not frappe.has_permission("Bin", "read"):
        frappe.throw("Stock balance read permission is required", frappe.PermissionError)

    warehouses = _warehouses(company)
    names = [w.name for w in warehouses]
    warehouse = (warehouse or "").strip()
    if warehouse and warehouse not in names:
        frappe.throw("Warehouse is not available for this shop", frappe.PermissionError)
    filtered_names = [warehouse] if warehouse else names

    fields = ["name", "item_name", "item_group", "stock_uom", "image",
              "has_serial_no", "has_batch_no"]
    if frappe.get_meta("Item").has_field("warranty_period"):
        fields.append("warranty_period")
    items = frappe.get_list(
        "Item", filters={"disabled": 0, "is_stock_item": 1},
        fields=fields, order_by="modified desc",
        limit_page_length=MAX_ITEMS + 1,
    )
    truncated = len(items) > MAX_ITEMS
    items = items[:MAX_ITEMS]
    indexed = {it.name: it for it in items}

    balances = {}
    if names and indexed:
        # Restrict warehouses before reading balances. Return only authorized items.
        bins = frappe.get_list(
            "Bin", filters={"warehouse": ["in", filtered_names]},
            fields=["item_code", "warehouse", "actual_qty", "reserved_qty",
                    "ordered_qty", "projected_qty", "valuation_rate", "stock_value"],
            limit_page_length=MAX_BINS + 1,
        )
        if len(bins) > MAX_BINS:
            frappe.throw("Inventory exceeds 15,000 warehouse balances; refine the shop setup")
        for b in bins:
            if b.item_code not in indexed:
                continue
            d = balances.setdefault(b.item_code, {"qty": 0, "reserved": 0,
                                                  "value": 0, "by_warehouse": []})
            qty = flt(b.actual_qty)
            d["qty"] += qty
            d["reserved"] += flt(b.reserved_qty)
            d["value"] += flt(b.stock_value)
            if qty or flt(b.reserved_qty):
                d["by_warehouse"].append({"warehouse": b.warehouse,
                                            "qty": qty,
                                            "reserved": flt(b.reserved_qty)})

    result = []
    for it in items:
        balance = balances.get(it.name, {"qty": 0, "reserved": 0,
                                         "value": 0, "by_warehouse": []})
        result.append({
            "item_code": it.name,
            "item_name": it.item_name or it.name,
            "item_group": it.item_group or "",
            "stock_uom": it.stock_uom or "Nos",
            "image": it.image or "",
            "warranty_days": it.get("warranty_period") or 0,
            "has_serial_no": int(it.get("has_serial_no") or 0),
            "has_batch_no": int(it.get("has_batch_no") or 0),
            "actual_qty": round(balance["qty"], 3),
            "reserved_qty": round(balance["reserved"], 3),
            "stock_value": round(balance["value"], 2),
            "by_warehouse": balance["by_warehouse"],
        })
    return {"company": company,
            "currency": frappe.db.get_value("Company", company, "default_currency") or "BDT",
            "warehouses": warehouses, "items": result,
            "truncated": truncated}


@frappe.whitelist(methods=["POST"])
def post_stock_movement(item_code=None, warehouse=None, qty=None,
                        movement=None, basic_rate=None, remarks=None):
    company = _shop_company()
    if not (frappe.has_permission("Stock Entry", "create") and
            frappe.has_permission("Stock Entry", "submit")):
        frappe.throw("Stock Entry create and submit permissions are required",
                     frappe.PermissionError)

    movement = (movement or "").strip().lower()
    if movement not in ("receive", "issue"):
        frappe.throw("Movement must be receive or issue")

    allowed = {w.name for w in _warehouses(company)}
    if not warehouse or warehouse not in allowed:
        frappe.throw("Choose an accessible warehouse in this shop")

    qty = flt(qty)
    if qty <= 0:
        frappe.throw("Quantity must be greater than zero")
    if not item_code or not frappe.has_permission("Item", "read", item_code):
        frappe.throw("Item is not accessible", frappe.PermissionError)
    item = frappe.get_doc("Item", item_code)
    if item.disabled or not item.is_stock_item:
        frappe.throw("Choose an active stock item")
    if item.has_serial_no or item.has_batch_no:
        frappe.throw("Serialized and batch-controlled items require their dedicated stock workflow")

    line = {"item_code": item_code, "qty": qty,
            "uom": item.stock_uom, "stock_uom": item.stock_uom,
            "conversion_factor": 1}
    if movement == "receive":
        basic_rate = flt(basic_rate)
        if basic_rate <= 0:
            frappe.throw("Enter a positive unit valuation rate for stock receipt")
        line.update({"t_warehouse": warehouse, "basic_rate": basic_rate})
        entry_type = "Material Receipt"
    else:
        line["s_warehouse"] = warehouse
        entry_type = "Material Issue"

    doc = frappe.get_doc({
        "doctype": "Stock Entry", "company": company,
        "stock_entry_type": entry_type, "purpose": entry_type,
        "remarks": (remarks or "")[:1000],
        "items": [line],
    })
    doc.insert()
    doc.submit()  # Only submitted documents affect the actual stock ledger.
    return {"stock_entry": doc.name, "docstatus": doc.docstatus,
            "movement": movement, "item_code": item_code,
            "qty": qty, "warehouse": warehouse}
