import frappe


@frappe.whitelist(methods=["GET"])
def get_service_receipt(job_name=None):
    if frappe.session.user == "Guest":
        frappe.throw("Login required", frappe.PermissionError)
    job_name = str(job_name or "").strip()
    if not job_name or len(job_name) > 140:
        frappe.throw("Valid Service Job number required")

    job = frappe.get_doc("Service Job", job_name)
    job.check_permission("read")
    shop = frappe.get_doc("Servicing Shop", job.shop)
    shop.check_permission("read")

    # SOS_RECEIVED_COMPONENTS_PRINT_V24: permission-checked custody rows,
    # sourced only from Service Job.custom_received_components; never shop stock.
    # SOS_CUSTOMER_RECEIPT_COMPONENTS_V25 — customer property only; permission checked above.
    from servicing_os.api.received_components_694 import snapshot
    received_components = snapshot(job)

    return {
        "job": {
            "name": job.name,
            "received_date": str(job.received_date or ""),
            "customer_name": job.customer_name or "",
            "mobile": job.mobile or "",
            "status": job.status or "",
            "priority": job.priority or "",
            "device_type": job.device_type or "",
            "brand": job.brand or "",
            "device_model": job.device_model or "",
            "serial_number": job.serial_number or "",
            "reported_problem": job.reported_problem or "",
            "accessories_received": job.accessories_received or "",
            "received_components": received_components,
            "estimated_cost": float(job.estimated_cost or 0),
            "expected_delivery": str(job.expected_delivery or ""),
        },
        "shop": {
            "name": shop.shop_name or shop.name,
            "address": shop.address or "",
            "phone": shop.phone or "",
            "currency": shop.currency or "BDT",
        },
    }
