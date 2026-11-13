import json
import frappe

# SERVICING_WORKSTATION_614D
ROLE = "Service Technician"
MARKER = "SERVICING_WORK_LOG_614D:"
STAGES = ("Inspection", "Diagnosis", "Repair", "Testing", "Parts Required", "Customer Update")
FIELDS = ["name", "status", "priority", "customer_name", "device_type", "brand", "device_model", "technician", "received_date", "modified"]


def _manager():
    return frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()


def _access():
    if frappe.session.user == "Guest":
        frappe.throw("Sign in to access technician jobs", frappe.PermissionError)
    if not _manager() and ROLE not in frappe.get_roles():
        frappe.throw("Service Technician role required", frappe.PermissionError)


def _assigned_job(name):
    _access()
    if not name or not frappe.db.exists("Service Job", name):
        frappe.throw("Service Job not found", frappe.DoesNotExistError)
    job = frappe.get_doc("Service Job", name)
    if not _manager() and job.technician != frappe.session.user:
        frappe.throw("You can only access your assigned Service Jobs", frappe.PermissionError)
    return job


def _timeline(name):
    comments = frappe.get_all(
        "Comment",
        filters={"reference_doctype": "Service Job", "reference_name": name,
                 "comment_type": "Comment", "content": ["like", MARKER + "%"]},
        fields=["name", "owner", "creation", "content"],
        order_by="creation desc", limit_page_length=100,
    )
    out = []
    for row in comments:
        try:
            parsed = json.loads(row.content[len(MARKER):])
            out.append({"name": row.name, "by": row.owner, "at": str(row.creation),
                        "stage": parsed.get("stage", "Repair"), "note": parsed.get("note", "")})
        except (ValueError, TypeError):
            continue
    return out


@frappe.whitelist()
def get_workstation(technician=None, status=None):
    _access()
    manager = _manager()
    user = frappe.session.user
    filters = {}
    if not manager:
        filters["technician"] = user
    elif technician and technician != "All":
        # An explicit technician filter only, no user-provided query conditions.
        if not frappe.db.exists("User", technician):
            frappe.throw("Unknown technician")
        filters["technician"] = technician
    if status and status != "All":
        permitted = ("Received", "Diagnosing", "Waiting for Parts", "Repairing",
                     "Completed", "Ready to Deliver", "Delivered", "Cancelled")
        if status not in permitted:
            frappe.throw("Unknown status")
        filters["status"] = status

    jobs = frappe.get_all("Service Job", filters=filters,
                          fields=FIELDS, order_by="modified desc", limit_page_length=200)
    for row in jobs:
        row.received_date = str(row.received_date or "")
        row.modified = str(row.modified or "")
    technicians = []
    if manager:
        names = frappe.get_all("Has Role", filters={"role": ROLE, "parenttype": "User"}, pluck="parent")
        if names:
            technicians = frappe.get_all("User", filters={"name": ["in", names], "enabled": 1},
                                         fields=["name", "full_name"], order_by="full_name asc")
    return {"current_user": user, "manager": manager, "jobs": jobs, "technicians": technicians,
            "count": len(jobs), "limited_to": 200}


@frappe.whitelist()
def get_job_worklog(job_name):
    job = _assigned_job(job_name)
    return {"job": {"name": job.name, "status": job.status, "technician": job.technician,
                    "customer_name": job.customer_name, "brand": job.brand,
                    "device_model": job.device_model, "reported_problem": job.reported_problem},
            "logs": _timeline(job.name)}


@frappe.whitelist(methods=["POST"])
def add_work_note(job_name, stage, note):
    job = _assigned_job(job_name)
    stage = (stage or "").strip()
    note = (note or "").strip()
    if stage not in STAGES:
        frappe.throw("Select a valid repair activity")
    if not 3 <= len(note) <= 3000:
        frappe.throw("Work note must be between 3 and 3000 characters")
    if job.status in ("Delivered", "Cancelled"):
        frappe.throw("Closed jobs cannot receive new repair activity")
    payload = MARKER + json.dumps({"stage": stage, "note": note}, ensure_ascii=False)
    # This privileged insert is allowed only after explicit role/assignment checks.
    comment = frappe.get_doc({"doctype": "Comment", "comment_type": "Comment",
                              "reference_doctype": "Service Job", "reference_name": job.name,
                              "content": payload})
    comment.insert(ignore_permissions=True)
    return {"saved": True, "job": job.name, "entry": comment.name,
            "logs": _timeline(job.name)}
