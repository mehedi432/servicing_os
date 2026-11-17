"""Technician assignment from SERVICING OS Counter (Frappe 15).

No permissions are bypassed for writing Service Jobs. No stock/payment data changed.
"""
import frappe
from frappe import _

PREFERRED = (
    "technician", "assigned_technician", "custom_assigned_technician",
    "technician_employee", "service_technician", "assigned_to_technician",
)


def _field():
    meta = frappe.get_meta("Service Job")
    options = []
    for f in meta.fields:
        if f.fieldtype == "Link" and f.options in ("Employee", "User") and not f.read_only:
            options.append(f)
    # Prefer Employee links; most shop technicians need no ERPNext User account.
    for link_type in ("Employee", "User"):
        for name in PREFERRED:
            for f in options:
                if f.fieldname == name and f.options == link_type:
                    return f
    extras = [f for f in options if "technician" in (f.fieldname or "").lower() or "technician" in (f.label or "").lower()]
    if len(extras) == 1:
        return extras[0]
    return None


def ensure_technician_field():
    """Bench setup command. Preserves any suitable existing technician Link field."""
    if frappe.session.user not in ("Administrator",) and "System Manager" not in frappe.get_roles():
        frappe.throw(_("System Manager permission required"), frappe.PermissionError)
    chosen = _field()
    if chosen:
        print("PASS: existing technician field: {} ({})".format(chosen.fieldname, chosen.options))
        return chosen.fieldname
    custom = frappe.db.exists("Custom Field", "Service Job-custom_assigned_technician")
    if custom:
        frappe.throw(_("A conflicting custom_assigned_technician field exists; no changes made"))
    meta = frappe.get_meta("Service Job")
    if not meta:
        frappe.throw(_("Service Job DocType is not installed"))
    fields = [f.fieldname for f in meta.fields if f.fieldname]
    insert_after = "status" if "status" in fields else "customer" if "customer" in fields else fields[-1] if fields else None
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    data = {
        "fieldname": "custom_assigned_technician",
        "label": "Assigned Technician",
        "fieldtype": "Link",
        "options": "Employee",
        "description": "Technician assigned from SERVICING OS Counter",
        "in_list_view": 1,
    }
    if insert_after:
        data["insert_after"] = insert_after
    create_custom_field("Service Job", data)
    frappe.clear_cache(doctype="Service Job")
    frappe.db.commit()  # setup command is an explicit administrative operation
    print("CREATED: Service Job.custom_assigned_technician (Link / Employee)")
    return "custom_assigned_technician"


def _require_access():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in"), frappe.PermissionError)
    if not (frappe.has_permission("Service Job", ptype="write") or frappe.has_permission("Service Job", ptype="create")):
        frappe.throw(_("You do not have permission to manage Service Jobs"), frappe.PermissionError)


@frappe.whitelist()
def get_counter_technicians():
    """Return only the minimal fields required for assignment UI."""
    _require_access()
    target = _field()
    if not target:
        return {"setup_needed": True, "field": None, "technicians": [], "jobs": []}
    workers = frappe.get_all(
        "Employee", filters={"status": "Active"},
        fields=["name", "employee_name", "user_id"],
        order_by="employee_name asc", limit_page_length=300,
    )
    employees = []
    for worker in workers:
        if target.options == "User" and not worker.user_id:
            continue
        employees.append({
            "value": worker.name,
            "label": worker.employee_name or worker.name,
        })
    meta = frappe.get_meta("Service Job")
    fields = ["name", target.fieldname]
    for key in ("customer_name", "status"):
        if meta.has_field(key):
            fields.append(key)
    jobs = frappe.get_list(
        "Service Job", fields=fields,
        order_by="modified desc", limit_page_length=40,
    )
    return {
        "setup_needed": False,
        "field": target.fieldname,
        "technicians": employees,
        "jobs": [
            {
                "name": job.name,
                "customer_name": job.get("customer_name") or "",
                "status": job.get("status") or "",
                "assigned_employee": (
                    frappe.db.get_value("Employee", {"user_id": job.get(target.fieldname)}, "name")
                    if target.options == "User" and job.get(target.fieldname) else job.get(target.fieldname)
                ) or "",
            }
            for job in jobs
        ],
    }


@frappe.whitelist(methods=["POST"])
def assign_counter_technician(job_name=None, employee=None):
    _require_access()
    if not job_name or not employee:
        frappe.throw(_("Select a Service Job and technician"))
    target = _field()
    if not target:
        frappe.throw(_("Technician field is not configured. Ask a System Manager to run setup."))
    job = frappe.get_doc("Service Job", str(job_name))
    job.check_permission("write")
    worker = frappe.db.get_value("Employee", str(employee), ["employee_name", "status", "user_id"], as_dict=True)
    if not worker or worker.status != "Active":
        frappe.throw(_("Choose an active Employee"))
    value = str(employee) if target.options == "Employee" else worker.user_id
    if not value:
        frappe.throw(_("This Employee is not linked to an ERPNext User"))
    job.set(target.fieldname, value)
    job.save()
    return {
        "ok": True,
        "job": job.name,
        "employee": str(employee),
        "employee_name": worker.employee_name or str(employee),
        "field": target.fieldname,
    }
