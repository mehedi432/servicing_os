
import frappe


@frappe.whitelist()
def get_app_info():
    user = frappe.session.user

    if user == "Guest":
        frappe.throw(
            "Please log in to use SERVICING OS",
            frappe.PermissionError
        )

    return {
        "app_name": "servicing_os",
        "app_title": "SERVICING OS",
        "version": "0.0.1",
        "user": user,
        "full_name": frappe.utils.get_fullname(user),
        "currency": (
            frappe.db.get_single_value(
                "Global Defaults",
                "default_currency"
            ) or "BDT"
        ),
        "features": {
            "retail_pos": False,
            "service_receive": False,
            "service_delivery": False,
            "used_laptops": False,
            "inventory": False
        }
    }
