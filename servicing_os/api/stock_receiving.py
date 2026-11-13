
import frappe
from frappe.utils import flt

COMPANY = "AL MODINA COMPUTERS LIMITED"
WAREHOUSE = "Spare Parts - AMCL"


@frappe.whitelist()
def get_stock_overview():
    if not frappe.has_permission("Item", "read"):
        frappe.throw("Item read permission required", frappe.PermissionError)

    if not frappe.has_permission("Warehouse", "read"):
        frappe.throw("Warehouse read permission required", frappe.PermissionError)

    warehouse = frappe.get_doc("Warehouse", WAREHOUSE)
    warehouse.check_permission("read")

    items = frappe.get_list(
        "Item",
        filters={
            "is_stock_item": 1,
            "is_sales_item": 1,
            "disabled": 0,
        },
        fields=["name", "item_name", "stock_uom", "item_group"],
        order_by="item_name asc",
        limit_page_length=500,
    )

    result = []

    for item in items:
        bin_data = frappe.db.get_value(
            "Bin",
            {
                "item_code": item.name,
                "warehouse": WAREHOUSE,
            },
            ["actual_qty", "reserved_qty"],
            as_dict=True,
        )

        actual = flt(bin_data.actual_qty) if bin_data else 0
        reserved = flt(bin_data.reserved_qty) if bin_data else 0

        result.append({
            "item_code": item.name,
            "item_name": item.item_name,
            "item_group": item.item_group,
            "uom": item.stock_uom,
            "actual_qty": actual,
            "reserved_qty": reserved,
            "available_qty": actual - reserved,
        })

    return {
        "company": COMPANY,
        "warehouse": WAREHOUSE,
        "items": result,
        "count": len(result),
    }


@frappe.whitelist(methods=["POST"])
def create_draft_purchase_receipt(supplier, items):
    """Create a draft only. Never submits a stock transaction."""

    if not frappe.has_permission("Purchase Receipt", "create"):
        frappe.throw(
            "Purchase Receipt create permission required",
            frappe.PermissionError,
        )

    if not supplier or not frappe.db.exists("Supplier", supplier):
        frappe.throw("Select a valid Supplier.")

    if frappe.db.get_value("Supplier", supplier, "disabled"):
        frappe.throw("Supplier is disabled.")

    if isinstance(items, str):
        items = frappe.parse_json(items)

    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        frappe.throw("Provide between 1 and 100 part rows.")

    warehouse = frappe.get_doc("Warehouse", WAREHOUSE)
    if warehouse.company != COMPANY or warehouse.is_group or warehouse.disabled:
        frappe.throw("Invalid receiving warehouse.")

    receipt_items = []

    for index, row in enumerate(items, 1):
        if not isinstance(row, dict):
            frappe.throw(f"Invalid row {index}.")

        code = str(row.get("item_code") or "").strip()

        if not frappe.db.exists("Item", code):
            frappe.throw(f"Unknown Item in row {index}.")

        item = frappe.get_doc("Item", code)

        if item.disabled or not item.is_stock_item or not item.is_purchase_item:
            frappe.throw(f"Item {code} is not an active purchasable stock Item.")

        try:
            qty = float(row.get("qty"))
            rate = float(row.get("rate"))
        except (TypeError, ValueError):
            frappe.throw(f"Invalid quantity or purchase rate in row {index}.")

        import math
        if not math.isfinite(qty) or not math.isfinite(rate):
            frappe.throw(f"Non-finite quantity or rate in row {index}.")

        if qty <= 0 or rate < 0:
            frappe.throw(f"Invalid quantity or purchase rate in row {index}.")

        receipt_items.append({
            "item_code": code,
            "item_name": item.item_name,
            "qty": qty,
            "rate": rate,
            "uom": item.stock_uom,
            "stock_uom": item.stock_uom,
            "conversion_factor": 1,
            "warehouse": WAREHOUSE,
        })

    receipt = frappe.get_doc({
        "doctype": "Purchase Receipt",
        "supplier": supplier,
        "company": COMPANY,
        "set_warehouse": WAREHOUSE,
        "items": receipt_items,
    })

    # Standard ERPNext permission checks and validations.
    # Buying Settings may require an existing Purchase Order.
    receipt.insert()

    return {
        "success": True,
        "purchase_receipt": receipt.name,
        "docstatus": receipt.docstatus,
        "items_count": len(receipt_items),
        "stock_posted": False,
        "message": "Draft created. Review and submit in ERPNext.",
    }
