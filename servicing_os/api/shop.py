import frappe

from servicing_os.api.site_company_706 import site_shop_context


@frappe.whitelist()
def get_shop_config():
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to SERVICING OS", frappe.PermissionError)
    context = site_shop_context()
    shop = frappe.get_doc("Servicing Shop", context["shop"])
    shop.check_permission("read")
    fields = (
        "name", "shop_name", "company", "phone", "address", "currency",
        "retail_warehouse", "used_laptop_warehouse", "spare_parts_warehouse", "is_active",
    )
    return {field: shop.get(field) for field in fields}
