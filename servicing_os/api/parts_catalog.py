import frappe
from frappe.utils import flt
from servicing_os.api.site_company_706 import current_company, spare_parts_warehouse

# SERVICING_PARTS_615C2
GROUP = "Computer Spare Parts"


def _access():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Sign in required", frappe.PermissionError)
    roles = set(frappe.get_roles(user))
    if not (user == "Administrator" or "System Manager" in roles
            or "Stock Manager" in roles or "Service Technician" in roles):
        frappe.throw("Service Job access required", frappe.PermissionError)


@frappe.whitelist()
def search_spare_parts(search=""):
    """Read-only stock Item lookup; shows zero-stock items without creating transactions."""
    _access()
    search = (search or "").strip()[:80]
    filters = {"disabled": 0, "is_stock_item": 1, "is_sales_item": 1}
    or_filters = None
    if search:
        match = "%" + search + "%"
        or_filters = [["Item", "item_code", "like", match],
                      ["Item", "item_name", "like", match]]
    items = frappe.get_all(
        "Item", filters=filters, or_filters=or_filters,
        fields=["name", "item_name", "stock_uom", "description"],
        order_by="item_name asc", limit_page_length=100,
    )
    codes = [item.name for item in items]
    quantities = {}
    if codes:
        bins = frappe.get_all("Bin", filters={"warehouse": spare_parts_warehouse(),
                         "item_code": ["in", codes]},
                         fields=["item_code", "actual_qty"])
        quantities = {row.item_code: flt(row.actual_qty) for row in bins}
    return {"items": [{"item_code": item.name, "item_name": item.item_name,
                       "uom": item.stock_uom,
                       "available_qty": quantities.get(item.name, 0)} for item in items],
            "warehouse": spare_parts_warehouse()}


@frappe.whitelist()
def get_request_lines(material_request):
    """Read only lines for a request, gated by existing job-level permission checks."""
    _access()
    from servicing_os.api.parts_request import check_job_access
    if not material_request:
        frappe.throw("Material Request is required")
    mr = frappe.get_doc("Material Request", material_request)
    if (mr.company != current_company() or mr.material_request_type != "Material Issue"
            or not mr.get("custom_service_job")):
        frappe.throw("Not a Service Job parts request", frappe.PermissionError)
    check_job_access(mr.custom_service_job)
    return {"name": mr.name, "job": mr.custom_service_job,
            "status": mr.status, "docstatus": mr.docstatus,
            "items": [{"item_code": row.item_code, "item_name": row.item_name,
                       "qty": row.qty, "uom": row.uom} for row in mr.items]}
