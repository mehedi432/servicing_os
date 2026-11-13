import frappe

# AMCL_STOCK_MANAGEMENT_615E3
COMPANY = "AL MODINA COMPUTERS LIMITED"
WAREHOUSE = "Spare Parts - AMCL"


def _check_read():
    if not frappe.has_permission("Item", "read") or not frappe.has_permission("Warehouse", "read"):
        frappe.throw("Stock access is not permitted for this user.", frappe.PermissionError)


@frappe.whitelist()
def get_stock_hub():
    """Read-only supplier options, draft receipts and request counts."""
    _check_read()
    from servicing_os.api.stock_receiving import get_stock_overview
    stock = get_stock_overview()
    can_create_receipt = bool(frappe.has_permission("Purchase Receipt", "create"))
    can_read_receipt = bool(frappe.has_permission("Purchase Receipt", "read"))
    suppliers = []
    if can_create_receipt and frappe.has_permission("Supplier", "read"):
        suppliers = frappe.get_list("Supplier", filters={"disabled": 0},
            fields=["name", "supplier_name"], order_by="supplier_name asc", limit_page_length=200)
    receipts = []
    if can_read_receipt:
        receipts = frappe.get_list("Purchase Receipt", filters={"company": COMPANY},
            fields=["name", "supplier", "posting_date", "docstatus", "grand_total"],
            order_by="modified desc", limit_page_length=30)
    pending_requests = []
    if frappe.has_permission("Material Request", "read"):
        pending_requests = frappe.get_list("Material Request", filters={
            "company": COMPANY, "material_request_type": "Material Issue",
            "docstatus": 1, "status": ["not in", ["Stopped", "Cancelled", "Issued"]],
        }, fields=["name", "status", "transaction_date", "custom_service_job"],
            order_by="modified desc", limit_page_length=30)
    return {
        "stock": stock, "suppliers": suppliers, "receipts": receipts,
        "pending_requests": pending_requests,
        "can_create_receipt": can_create_receipt,
        "can_read_receipt": can_read_receipt,
    }
