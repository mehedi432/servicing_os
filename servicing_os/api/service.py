import json
import re

import frappe
from servicing_os.api.customer import resolve_customer, normalize_mobile
from frappe.utils import now_datetime, flt


def clean(value):
    return str(value or "").strip()


def normalize_mobile(value):
    return re.sub(r"[\s\-()]", "", clean(value))


def find_customer(mobile):
    if not mobile:
        return None

    matches = frappe.get_list(
        "Customer",
        filters={"mobile_no": mobile},
        fields=["name"],
        limit_page_length=1,
    )
    return matches[0].name if matches else None


@frappe.whitelist(methods=["POST"])
def receive_service_job(data=None):
    if frappe.session.user == "Guest":
        frappe.throw(
            "Please log in to SERVICING OS",
            frappe.PermissionError,
        )

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (ValueError, TypeError):
            frappe.throw("Invalid JSON payload")

    if not isinstance(data, dict):
        frappe.throw("Service job data must be an object")

    shop = clean(data.get("shop")) or "AL MODINA COMPUTERS LIMITED"

    if not frappe.db.exists(
        "Servicing Shop",
        {"name": shop, "is_active": 1},
    ):
        frappe.throw("Invalid or inactive shop")

    if not frappe.has_permission(
        "Servicing Shop", "read", doc=shop
    ):
        frappe.throw("No permission to access this shop")

    if not frappe.has_permission("Service Job", "create"):
        frappe.throw(
            "No permission to create service jobs",
            frappe.PermissionError,
        )

    customer_name = clean(data.get("customer_name"))
    mobile = normalize_mobile(data.get("mobile"))
    device_type = clean(data.get("device_type"))
    reported_problem = clean(data.get("reported_problem"))

    if not customer_name:
        frappe.throw("Customer name is required")

    if not mobile:
        frappe.throw("Customer mobile number is required")

    if not device_type:
        frappe.throw("Device type is required")

    if not reported_problem:
        frappe.throw("Reported problem is required")

    valid_devices = [
        "Laptop", "Desktop", "Monitor", "Printer", "Other"
    ]
    if device_type not in valid_devices:
        frappe.throw("Invalid device type")

    priority = clean(data.get("priority")) or "Normal"
    if priority not in ["Normal", "High", "Urgent"]:
        frappe.throw("Invalid priority")

    estimated_cost = flt(data.get("estimated_cost"))
    if estimated_cost < 0:
        frappe.throw("Estimated cost cannot be negative")

    customer, customer_created = resolve_customer(
        customer_name,
        mobile,
        data.get("customer"),
    )

    job = frappe.get_doc({
        "doctype": "Service Job",
        "shop": shop,
        "received_date": now_datetime(),
        "status": "Received",
        "priority": priority,
        "customer": customer,
        "customer_name": customer_name,
        "mobile": mobile,
        "device_type": device_type,
        "brand": clean(data.get("brand")),
        "device_model": clean(data.get("device_model")),
        "serial_number": clean(data.get("serial_number")),
        "reported_problem": reported_problem,
        "accessories_received": clean(
            data.get("accessories_received")
        ),
        "estimated_cost": estimated_cost,
        "remarks": clean(data.get("remarks")),
    })

    # SOS_RECEIVE_INLINE_TECH_HISTORY_682: same transaction as intake; validates active Employee.
    from servicing_os.api.counter_receive_682 import assign_technician_on_create
    assign_technician_on_create(job, data.get("assigned_technician"))
    # SOS_DEVICE_COMPONENTS_694: record customer property in the same Service Job transaction.
    from servicing_os.api.received_components_694 import apply_to_job
    if 'received_components' in data:
        apply_to_job(job, data['received_components'])
    job.insert()

    return {
        "success": True,
        "service_job": job.name,
        "status": job.status,
        "customer": job.customer,
        "customer_created": customer_created,
        "customer_name": job.customer_name,
        "mobile": job.mobile,
        "device_type": job.device_type,
        "estimated_cost": job.estimated_cost,
    }


@frappe.whitelist()
def get_recent_service_jobs(limit=10):
    if frappe.session.user == "Guest":
        frappe.throw(
            "Please log in to SERVICING OS",
            frappe.PermissionError,
        )

    limit = max(1, min(int(limit), 50))

    return frappe.get_list(
        "Service Job",
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
            "estimated_cost",
        ],
        order_by="creation desc",
        limit_page_length=limit,
    )
