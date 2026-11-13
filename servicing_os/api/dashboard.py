import frappe
from frappe.utils import today


@frappe.whitelist()
def get_dashboard():
    if frappe.session.user == "Guest":
        frappe.throw(
            "Please log in to SERVICING OS",
            frappe.PermissionError
        )

    if not frappe.has_permission("Service Job", "read"):
        frappe.throw(
            "No permission to read Service Jobs",
            frappe.PermissionError
        )

    shops = frappe.get_list(
        "Servicing Shop",
        filters={"is_active": 1},
        fields=["name"],
        limit_page_length=1
    )

    if not shops:
        frappe.throw("No accessible active shop found")

    shop = shops[0].name

    jobs = frappe.get_list(
        "Service Job",
        filters={"shop": shop},
        fields=[
            "name",
            "customer_name",
            "mobile",
            "device_type",
            "brand",
            "device_model",
            "status",
            "priority",
            "received_date",
            "estimated_cost"
        ],
        order_by="creation desc",
        limit_page_length=20
    )

    today_start = today() + " 00:00:00"
    tomorrow_start = frappe.utils.add_days(
        today(), 1
    ) + " 00:00:00"

    received_today = frappe.db.count(
        "Service Job",
        {
            "shop": shop,
            "received_date": [
                "between",
                [today_start, tomorrow_start]
            ]
        }
    )

    ready_to_deliver = frappe.db.count(
        "Service Job",
        {
            "shop": shop,
            "status": "Ready to Deliver"
        }
    )

    pending_jobs = frappe.db.count(
        "Service Job",
        {
            "shop": shop,
            "status": [
                "not in",
                ["Delivered", "Cancelled"]
            ]
        }
    )

    return {
        "shop": shop,
        "received_today": received_today,
        "ready_to_deliver": ready_to_deliver,
        "pending_jobs": pending_jobs,
        "recent_jobs": jobs
    }
