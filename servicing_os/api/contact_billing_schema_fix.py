"""Restore the ERPNext-provided Contact.is_billing_contact field only."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# SERVICING_OS_CONTACT_BILLING_SCHEMA_630
FIELD = "is_billing_contact"
DT = "Contact"


def _state():
    meta = frappe.get_meta(DT, cached=False)
    df = meta.get_field(FIELD)
    cf = frappe.db.get_value(
        "Custom Field", {"dt": DT, "fieldname": FIELD}, "name"
    )
    return {
        "doctype": DT,
        "fieldname": FIELD,
        "metadata_field_exists": bool(df),
        "metadata_fieldtype": df.fieldtype if df else None,
        "custom_field_record": cf,
        "database_column_exists": bool(frappe.db.has_column(DT, FIELD)),
        "primary_contact_column_exists": bool(frappe.db.has_column(DT, "is_primary_contact")),
    }


def check():
    """Read-only preflight. No fixtures, customers or invoices are created."""
    state = _state()
    if state["database_column_exists"]:
        # Verify the exact type of filter used by the accounts/party path.
        frappe.get_all(DT, filters={FIELD: 1}, fields=["name"], limit_page_length=1)
        state["filter_query_works"] = True
    else:
        state["filter_query_works"] = False
    state["ready"] = bool(state["database_column_exists"] and state["filter_query_works"])
    return state


def apply():
    """Safe, repeatable field/schema repair; no financial document operations."""
    if "erpnext" not in frappe.get_installed_apps():
        frappe.throw("ERPNext is not installed on this site. Refusing schema changes.")
    state = _state()
    if not state["primary_contact_column_exists"]:
        frappe.throw("Contact.is_primary_contact is also missing; requires broader schema investigation.")
    if state["metadata_field_exists"] and state["metadata_fieldtype"] != "Check":
        frappe.throw("Contact.is_billing_contact exists with unexpected field type; no changes made.")
    if state["database_column_exists"] and state["metadata_field_exists"]:
        return {"action": "already_correct", "verification": check()}

    if not state["metadata_field_exists"]:
        if state["custom_field_record"]:
            frappe.clear_cache(doctype=DT)
            state = _state()
            if not state["metadata_field_exists"]:
                frappe.throw("Custom Field record exists but metadata is inconsistent; no changes made.")
        else:
            create_custom_fields({DT: [{
                "label": "Is Billing Contact",
                "fieldname": FIELD,
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "is_primary_contact",
            }]}, update=False)

    # In case metadata was present but the physical column never synced.
    frappe.clear_cache(doctype=DT)
    if not frappe.db.has_column(DT, FIELD):
        frappe.db.updatedb(DT)
        frappe.clear_cache(doctype=DT)

    verified = check()
    if not verified["ready"]:
        frappe.throw("Field schema sync did not pass verification; inspect database before retrying.")
    frappe.db.commit()
    return {"action": "restored_contact_billing_field", "verification": verified}
