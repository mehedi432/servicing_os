import frappe

# AMCL_QUICK_ASSIGN_615E1
ROLE = "Service Technician"
MANAGERS = {"System Manager"}
FINAL = {"Delivered", "Cancelled"}


def _require_manager():
    user = frappe.session.user
    if user == "Guest" or not (user == "Administrator" or MANAGERS.intersection(set(frappe.get_roles(user)))):
        frappe.throw("Only a service manager can assign technicians.", frappe.PermissionError)
    return user


def _technicians():
    names = frappe.get_all(
        "Has Role",
        filters={"role": ROLE, "parenttype": "User"},
        pluck="parent",
        limit_page_length=1000,
    )
    if not names:
        return []
    return frappe.get_all(
        "User",
        filters={"name": ["in", list(set(names))], "enabled": 1, "user_type": "System User"},
        fields=["name", "full_name"],
        order_by="full_name asc",
        limit_page_length=1000,
    )


@frappe.whitelist()
def get_quick_assign_queue():
    _require_manager()
    if not frappe.has_permission("Service Job", ptype="read"):
        frappe.throw("No read permission for Service Job.", frappe.PermissionError)
    jobs = frappe.get_list(
        "Service Job",
        fields=["name", "status", "customer_name", "brand", "device_model", "technician", "modified"],
        filters={"status": ["not in", ["Delivered", "Cancelled"]]},
        order_by="modified desc",
        limit_page_length=100,
    )
    return {"jobs": jobs, "technicians": _technicians(), "count": len(jobs)}


@frappe.whitelist(methods=["POST"])
def assign_technician(job_name, technician, expected_modified=None):
    user = _require_manager()
    if not job_name or not technician:
        frappe.throw("Select a Service Job and technician.")
    doc = frappe.get_doc("Service Job", job_name)
    if not frappe.has_permission("Service Job", ptype="write", doc=doc):
        frappe.throw("No write permission for this Service Job.", frappe.PermissionError)
    if doc.status in FINAL:
        frappe.throw("Closed or cancelled jobs cannot be reassigned.")
    if expected_modified and str(doc.modified) != str(expected_modified):
        frappe.throw("This job changed in the meantime. Refresh and try again.")
    valid = {row.name for row in _technicians()}
    if technician not in valid:
        frappe.throw("Technician must be an enabled System User with Service Technician role.")
    before = doc.technician or "Unassigned"
    if before == technician:
        return {"changed": False, "job": doc.name, "technician": technician}
    doc.technician = technician
    doc.save()
    doc.add_comment("Comment", text=f"Technician reassigned from {before} to {technician} by {user}.")
    return {"changed": True, "job": doc.name, "technician": technician}
