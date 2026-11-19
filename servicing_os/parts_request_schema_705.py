"""SERVICING OS 7.05: idempotent schema for Spare Parts Requests.

Safe for existing and new Frappe v15 sites; no business document mutation.
"""
import frappe

DOCTYPE = "Material Request"
FIELD = "custom_service_job"
TARGET = "Service Job"


def ensure():
    """Synchronize the Service Job link on Material Request."""
    return ensure_service_job_link(
        DOCTYPE, "material_request_type", in_list_view=1, in_standard_filter=1,
    )


def ensure_service_job_link(doctype, insert_after, **properties):
    """Synchronize link metadata and its SQL column without editing records."""
    for dt in (doctype, TARGET):
        if not frappe.db.exists("DocType", dt):
            frappe.throw("SERVICING OS: required DocType missing: " + dt)

    frappe.clear_cache(doctype=doctype)
    field = get_service_job_link(doctype)

    action = "reused"
    if field is None:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        create_custom_fields({doctype: [{
            "fieldname": FIELD,
            "label": "Service Job",
            "fieldtype": "Link",
            "options": TARGET,
            "insert_after": insert_after,
            "no_copy": 1,
            **properties,
        }]}, update=False)
        action = "created"

    frappe.clear_cache(doctype=doctype)
    if not get_service_job_link(doctype):
        frappe.throw(f"SERVICING OS: {doctype}.{FIELD} was not synchronized")

    if not frappe.db.has_column(doctype, FIELD):
        # Repair sites where Custom Field metadata was copied but the SQL schema was not.
        frappe.db.updatedb(doctype)
        action = "synchronized_column"

    if not frappe.db.has_column(doctype, FIELD):
        frappe.throw(f"SERVICING OS: {doctype}.{FIELD} SQL column was not created")

    return {"status": "OK", "doctype": doctype, "field": FIELD,
            "options": TARGET, "action": action, "business_records_changed": False}


def get_service_job_link(doctype):
    field = frappe.get_meta(doctype, cached=False).get_field(FIELD)
    if field and (field.fieldtype != "Link" or field.options != TARGET):
        frappe.throw(f"SERVICING OS: {doctype}.{FIELD} must link to {TARGET}")
    return field
