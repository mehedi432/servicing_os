from servicing_os.api.technicians import validate_technician_assignment
# SERVICING_TECHNICIAN_ROLE_614C
import frappe
from frappe import _
from frappe.utils import now_datetime, getdate, flt

DOCTYPE = "Service Job"

STATUSES = (
    "Received",
    "Diagnosing",
    "Waiting for Parts",
    "Repairing",
    "Ready to Deliver",
    "Delivered",
    "Cancelled",
)

TRANSITIONS = {
    "Received": (
        "Diagnosing",
        "Cancelled",
    ),
    "Diagnosing": (
        "Waiting for Parts",
        "Repairing",
        "Cancelled",
    ),
    "Waiting for Parts": (
        "Diagnosing",
        "Repairing",
        "Cancelled",
    ),
    "Repairing": (
        "Waiting for Parts",
        "Ready to Deliver",
        "Cancelled",
    ),
    "Ready to Deliver": (
        "Repairing",
        "Delivered",
        "Cancelled",
    ),
    "Delivered": (),
    "Cancelled": (),
}

EDITABLE_FIELDS = (
    "technician",
    "diagnosis",
    "estimated_cost",
    "final_repair_cost",
    "expected_delivery",
    "remarks",
)


def get_job(name):
    if not name:
        frappe.throw(_("Service Job number is required."))

    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission("read")
    return doc


def serialize_job(doc):
    return {
        "name": doc.name,
        "status": doc.status,
        "priority": doc.priority,
        "customer": doc.customer,
        "customer_name": doc.customer_name,
        "mobile": doc.mobile,
        "device_type": doc.device_type,
        "brand": doc.brand,
        "device_model": doc.device_model,
        "serial_number": doc.serial_number,
        "reported_problem": doc.reported_problem,
        "accessories_received": doc.accessories_received,
        "technician": doc.technician,
        "diagnosis": doc.diagnosis,
        "estimated_cost": doc.estimated_cost,
        "final_repair_cost": doc.final_repair_cost,
        "received_date": doc.received_date,
        "expected_delivery": doc.expected_delivery,
        "actual_delivery": doc.actual_delivery,
        "remarks": doc.remarks,
        "modified": str(doc.modified),
    }


@frappe.whitelist(methods=["GET"])
def get_repair_job(job_name=None):
    doc = get_job(job_name)
    return {
        "job": serialize_job(doc),
        "allowed_next_statuses": list(
            TRANSITIONS.get(doc.status, ())
        ),
    }


@frappe.whitelist(methods=["GET"])
def list_repair_jobs(status=None, search=None, limit=50):
    frappe.has_permission(
        DOCTYPE,
        ptype="read",
        throw=True,
    )

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50

    limit = max(1, min(limit, 100))

    filters = {}

    if status and status != "All":
        if status not in STATUSES:
            frappe.throw(_("Invalid status filter."))
        filters["status"] = status

    or_filters = None

    if search:
        search = str(search).strip()[:100]
        if search:
            or_filters = [
                [DOCTYPE, "name", "like", "%" + search + "%"],
                [DOCTYPE, "customer_name", "like", "%" + search + "%"],
                [DOCTYPE, "mobile", "like", "%" + search + "%"],
                [DOCTYPE, "serial_number", "like", "%" + search + "%"],
            ]

    jobs = frappe.get_list(
        DOCTYPE,
        fields=[
            "name",
            "status",
            "priority",
            "customer_name",
            "mobile",
            "device_type",
            "brand",
            "device_model",
            "technician",
            "received_date",
            "modified",
        ],
        filters=filters,
        or_filters=or_filters,
        order_by="modified desc",
        page_length=limit,
    )

    return {
        "jobs": jobs,
        "statuses": list(STATUSES),
    }


@frappe.whitelist(methods=["POST"])
def update_repair_job(
    job_name=None,
    status=None,
    technician=None,
    diagnosis=None,
    estimated_cost=None,
    final_repair_cost=None,
    expected_delivery=None,
    remarks=None,
    expected_modified=None,
):
    doc = get_job(job_name)
    doc.check_permission("write")

    if doc.docstatus != 0:
        frappe.throw(
            _("Only draft Service Jobs can be updated.")
        )

    if expected_modified:
        if str(doc.modified) != str(expected_modified):
            frappe.throw(
                _("This Service Job was modified by another user. "
                  "Reload it before saving."),
                frappe.TimestampMismatchError,
            )

    previous_status = doc.status
    changes = []

    if status is not None:
        status = str(status).strip()

        if status not in STATUSES:
            frappe.throw(_("Invalid Service Job status."))

        if status != previous_status:
            allowed = TRANSITIONS.get(previous_status, ())

            if status not in allowed:
                frappe.throw(
                    _("Invalid status transition: {0} to {1}")
                    .format(previous_status, status)
                )

            # Check actual DocType Select options.
            status_field = doc.meta.get_field("status")

            if status_field and status_field.fieldtype == "Select":
                configured = [
                    value.strip()
                    for value in (status_field.options or "").splitlines()
                    if value.strip()
                ]

                if status not in configured:
                    frappe.throw(
                        _("Status {0} is not configured in Service Job.")
                        .format(status)
                    )

            doc.status = status
            changes.append(
                "Status: {} → {}".format(previous_status, status)
            )

    updates = {
        "technician": technician,
        "diagnosis": diagnosis,
        "estimated_cost": estimated_cost,
        "final_repair_cost": final_repair_cost,
        "expected_delivery": expected_delivery,
        "remarks": remarks,
    }

    for fieldname, value in updates.items():
        if value is None:
            continue

        if not doc.meta.has_field(fieldname):
            frappe.throw(
                _("Service Job field missing: {0}")
                .format(fieldname)
            )

        if fieldname in ("estimated_cost", "final_repair_cost"):
            try:
                value = flt(value)
            except (TypeError, ValueError):
                frappe.throw(
                    _("Invalid amount for {0}").format(fieldname)
                )

            if value < 0:
                frappe.throw(
                    _("Repair amounts cannot be negative.")
                )

        if fieldname == "expected_delivery" and value:
            try:
                value = getdate(value)
            except Exception:
                frappe.throw(_("Invalid expected delivery date."))

        old_value = doc.get(fieldname)

        if str(old_value or "") != str(value or ""):
            doc.set(fieldname, value)
            changes.append(
                "{} updated".format(fieldname.replace("_", " ").title())
            )

    if status == "Ready to Deliver":
        if not (doc.diagnosis or "").strip():
            frappe.throw(
                _("Diagnosis is required before marking a job ready.")
            )

    if status == "Delivered":
        if doc.final_repair_cost is None:
            frappe.throw(
                _("Final repair cost must be entered before delivery.")
            )

        doc.actual_delivery = now_datetime()

    if not changes:
        return {
            "job": serialize_job(doc),
            "changed": False,
        }

    validate_technician_assignment(doc.get('technician'))
    doc.save()

    # Native Frappe comments provide a human-readable
    # audit trail with the current authenticated user.
    doc.add_comment(
        "Comment",
        text="Repair workflow update by {}: {}".format(
            frappe.session.user,
            "; ".join(changes),
        ),
    )

    return {
        "job": serialize_job(doc),
        "changed": True,
        "changes": changes,
        "allowed_next_statuses": list(
            TRANSITIONS.get(doc.status, ())
        ),
    }


# AMCL_REPAIR_COMPLETED_616C — explicit completion before dispatch.
# Runs at module import, before any whitelisted method is called.
if isinstance(STATUSES, (tuple, list)):
    _amcl_states = list(STATUSES)
    if "Completed" not in _amcl_states:
        _amcl_states.insert(
            _amcl_states.index("Ready to Deliver") if "Ready to Deliver" in _amcl_states
            else len(_amcl_states), "Completed"
        )
    STATUSES = tuple(_amcl_states) if isinstance(STATUSES, tuple) else _amcl_states
else:
    raise RuntimeError("Unexpected Service Job STATUSES data type")
# Preserve existing transitions, but require Completed after Repairing.
_amcl_repairing = [x for x in TRANSITIONS.get("Repairing", ()) if x != "Ready to Deliver"]
if "Completed" not in _amcl_repairing:
    _amcl_repairing.insert(0, "Completed")
TRANSITIONS["Repairing"] = tuple(_amcl_repairing)
TRANSITIONS["Completed"] = ("Ready to Deliver", "Repairing", "Cancelled")
