import frappe

# SERVICING_TECHNICIAN_ROLE_614C

ROLE = "Service Technician"


def validate_technician_assignment(user_id):
    """Reject users who are not enabled Service Technicians."""

    if not user_id:
        return

    if not frappe.db.exists("User", user_id):
        frappe.throw(
            "Selected technician does not exist.",
            frappe.ValidationError,
        )

    enabled = frappe.db.get_value(
        "User", user_id, "enabled"
    )

    if not enabled:
        frappe.throw(
            "Selected technician is disabled.",
            frappe.ValidationError,
        )

    user_type = frappe.db.get_value(
        "User", user_id, "user_type"
    )

    if user_type != "System User":
        frappe.throw(
            "Technician must be a System User.",
            frappe.ValidationError,
        )

    # Check the user's explicitly assigned role.
    # Administrator is not automatically a technician.
    has_role = frappe.db.exists(
        "Has Role",
        {
            "parenttype": "User",
            "parent": user_id,
            "role": ROLE,
        },
    )

    if not has_role:
        frappe.throw(
            "Selected user does not have the "
            "Service Technician role.",
            frappe.ValidationError,
        )


@frappe.whitelist()
def list_technicians(search=""):
    if not frappe.has_permission(
        "Service Job", "read"
    ):
        frappe.throw(
            "Not permitted to read Service Jobs.",
            frappe.PermissionError,
        )

    if not frappe.has_permission(
        "Service Job", "write"
    ):
        frappe.throw(
            "Not permitted to assign technicians.",
            frappe.PermissionError,
        )

    search = (search or "").strip()[:100]

    assigned = frappe.get_all(
        "Has Role",
        filters={
            "role": ROLE,
            "parenttype": "User",
        },
        pluck="parent",
    )

    if not assigned:
        return {"technicians": []}

    filters = {
        "name": ["in", assigned],
        "enabled": 1,
        "user_type": "System User",
    }

    or_filters = None

    if search:
        pattern = "%" + search + "%"
        or_filters = [
            ["User", "name", "like", pattern],
            ["User", "full_name", "like", pattern],
        ]

    users = frappe.get_list(
        "User",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "full_name"],
        order_by="full_name asc",
        limit_page_length=100,
    )

    return {
        "technicians": [
            {
                "value": user.name,
                "label": user.full_name or user.name,
                "email": user.name,
            }
            for user in users
        ]
    }


def setup_service_technician_role():
    """Run from bench as an administrator maintenance task."""

    if not frappe.db.exists("Role", ROLE):
        role = frappe.get_doc({
            "doctype": "Role",
            "role_name": ROLE,
            "desk_access": 1,
        })
        role.insert(ignore_permissions=True)
        frappe.db.commit()

    return {
        "role": ROLE,
        "created_or_existing": True,
    }
