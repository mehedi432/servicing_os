import frappe


@frappe.whitelist()
def get_shop_config():
    if frappe.session.user == "Guest":
        frappe.throw(
            "Please log in to SERVICING OS",
            frappe.PermissionError
        )

    shops = frappe.get_all(
        "Servicing Shop",
        filters={"is_active": 1},
        fields=[
            "name",
            "shop_name",
            "company",
            "phone",
            "address",
            "currency",
            "retail_warehouse",
            "used_laptop_warehouse",
            "spare_parts_warehouse",
            "is_active",
        ],
        order_by="creation asc",
        limit_page_length=1,
    )

    if not shops:
        frappe.throw("No active SERVICING OS shop found")

    shop = shops[0]

    if not frappe.has_permission(
        "Servicing Shop",
        "read",
        doc=shop.name,
    ):
        frappe.throw(
            "You do not have permission to access this shop",
            frappe.PermissionError,
        )

    return shop
