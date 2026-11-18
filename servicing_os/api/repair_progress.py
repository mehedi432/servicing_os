import frappe
from frappe.utils import now_datetime
from servicing_os.api.lifecycle import TRANSITIONS

# AMCL_REPAIR_COMPLETED_616C
TECHNICIAN_ROLE = "Service Technician"
MANAGER_ROLES = {"System Manager"}
MANAGER_ONLY = {"Ready to Deliver", "Delivered", "Cancelled"}
from servicing_os.api.site_company_706 import current_company, validate_job_shop
def _manager():
    user = frappe.session.user
    return user == "Administrator" or bool(MANAGER_ROLES.intersection(frappe.get_roles(user)))


def _get_job(job_name):
    if not job_name or not frappe.db.exists("Service Job", job_name):
        frappe.throw("Service Job not found", frappe.DoesNotExistError)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Please log in", frappe.PermissionError)
    manager = _manager()
    doc = frappe.get_doc("Service Job", job_name)
    validate_job_shop(doc)
    if manager:
        if not frappe.has_permission("Service Job", "read", doc=doc):
            frappe.throw("Cannot read Service Job", frappe.PermissionError)
    elif TECHNICIAN_ROLE not in frappe.get_roles(user) or doc.technician != user:
        frappe.throw("Only your assigned repairs are accessible", frappe.PermissionError)
    return doc, manager


def _allowed(doc, manager):
    options = list(TRANSITIONS.get(doc.status, ()))
    if not manager:
        options = [s for s in options if s not in MANAGER_ONLY]
    return options


@frappe.whitelist()
def get_progress(job_name):
    doc, manager = _get_job(job_name)
    return {
        "job": doc.name,
        "status": doc.status,
        "technician": doc.technician,
        "modified": str(doc.modified),
        "manager": manager,
        "allowed_next_statuses": _allowed(doc, manager),
    }


@frappe.whitelist(methods=["POST"])
def advance_repair(job_name, next_status, expected_modified=None):
    doc, manager = _get_job(job_name)
    if not manager and doc.technician != frappe.session.user:
        frappe.throw("Not your assigned repair", frappe.PermissionError)
    if next_status not in _allowed(doc, manager):
        frappe.throw("Invalid transition or insufficient permission: " + str(next_status))
    if expected_modified and str(doc.modified) != str(expected_modified):
        frappe.throw("This repair changed. Refresh and try again.")
    previous = doc.status
    if previous == next_status:
        return {"changed": False, "job": doc.name, "status": doc.status}
    if manager and not frappe.has_permission("Service Job", "write", doc=doc):
        frappe.throw("Cannot edit this Service Job", frappe.PermissionError)
    doc.status = next_status
    if next_status == "Delivered" and doc.meta.has_field("actual_delivery"):
        doc.actual_delivery = now_datetime()
    # Technicians receive narrowly scoped authority only for their assigned
    # jobs and permitted status transitions. Regular document validations run.
    if manager:
        doc.save()
    else:
        doc.save(ignore_permissions=True)
    doc.add_comment("Comment", text=f"Repair status: {previous} → {next_status} (by {frappe.session.user})")
    return {"changed": True, "job": doc.name, "status": doc.status,
            "allowed_next_statuses": _allowed(doc, manager), "modified": str(doc.modified)}


def setup_completed_option():
    """Site maintenance action (bench execute). Uses a standard property setter."""
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    meta = frappe.get_meta("Service Job")
    field = meta.get_field("status")
    if not field or field.fieldtype != "Select":
        frappe.throw("Expected Service Job.status Select field")
    old = [x.strip() for x in (field.options or "").splitlines() if x.strip()]
    required = {"Received", "Diagnosing", "Waiting for Parts", "Repairing",
                "Ready to Deliver", "Delivered", "Cancelled"}
    if not required.issubset(set(old)):
        frappe.throw("Status options differ from expected. No changes made.")
    if "Completed" in old:
        return {"updated": False, "statuses": old}
    old.insert(old.index("Ready to Deliver"), "Completed")
    make_property_setter("Service Job", "status", "options", "\n".join(old), "Text")
    frappe.clear_cache(doctype="Service Job")
    current = frappe.get_meta("Service Job", cached=False).get_field("status").options or ""
    if "Completed" not in current.splitlines():
        frappe.throw("Completed status did not appear in metadata")
    return {"updated": True, "statuses": old}
