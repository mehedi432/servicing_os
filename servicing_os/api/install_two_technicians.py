import frappe
import json

ROLE = "Service Technician"

TECHNICIANS = [
    ("rasel@amcl.com", "Rasel", "Mahmud"),
    ("shakawat@amcl.com", "Shakfwat", "Khan"),
]


def install():
    created = []
    existing = []
    assigned = []

    try:
        # Validate existing accounts before making changes.
        for email, first, last in TECHNICIANS:
            if frappe.db.exists("User", email):
                user = frappe.get_doc("User", email)

                if not user.enabled:
                    raise Exception(
                        f"{email} is disabled. No changes made."
                    )

                if user.user_type != "System User":
                    raise Exception(
                        f"{email} is not a System User."
                    )

        # Create role if missing.
        if not frappe.db.exists("Role", ROLE):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": ROLE,
                "desk_access": 1,
            }).insert(ignore_permissions=True)

        for email, first, last in TECHNICIANS:
            if frappe.db.exists("User", email):
                user = frappe.get_doc("User", email)
                existing.append(email)
            else:
                user = frappe.get_doc({
                    "doctype": "User",
                    "email": email,
                    "first_name": first,
                    "last_name": last,
                    "enabled": 1,
                    "user_type": "System User",
                    "send_welcome_email": 0,
                })

                user.flags.no_welcome_mail = True
                user.insert(ignore_permissions=True)
                created.append(email)

            # Preserve all existing roles.
            current_roles = {
                row.role for row in user.roles
            }

            if ROLE not in current_roles:
                user.append("roles", {
                    "role": ROLE,
                })
                user.flags.no_welcome_mail = True
                user.save(ignore_permissions=True)
                assigned.append(email)

        frappe.db.commit()

        result = {
            "success": True,
            "created": created,
            "existing_preserved": existing,
            "role_assigned": assigned,
        }

        print(json.dumps(result, indent=2))
        return result

    except Exception:
        frappe.db.rollback()
        raise
