"""SERVICING OS 7.05: idempotent schema for Spare Parts Requests.

Safe for existing and new Frappe v15 sites; no business document mutation.
"""
import frappe

DOCTYPE = "Material Request"
FIELD = "custom_service_job"
TARGET = "Service Job"


def ensure():
    """Create/repair the ERPNext Link field metadata/column without modifying records."""
    for dt in (DOCTYPE, TARGET):
        if not frappe.db.exists("DocType", dt):
            frappe.throw("SERVICING OS 7.05: required DocType missing: " + dt)

    frappe.clear_cache(doctype=DOCTYPE)
    field = frappe.get_meta(DOCTYPE, cached=False).get_field(FIELD)
    if field and (field.fieldtype != "Link" or field.options != TARGET):
        frappe.throw(
            "SERVICING OS 7.05: existing Material Request.custom_service_job "
            "has incompatible fieldtype/options; refusing to overwrite"
        )

    action = "reused"
    if field is None:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        create_custom_fields({DOCTYPE: [{
            "fieldname": FIELD,
            "label": "Service Job",
            "fieldtype": "Link",
            "options": TARGET,
            "insert_after": "material_request_type",
            "in_list_view": 1,
            "in_standard_filter": 1,
            "no_copy": 1,
        }]}, update=False)
        action = "created"

    frappe.clear_cache(doctype=DOCTYPE)
    field = frappe.get_meta(DOCTYPE, cached=False).get_field(FIELD)
    if not field or field.fieldtype != "Link" or field.options != TARGET:
        frappe.throw("SERVICING OS 7.05: Material Request link field was not synchronized")

    if not frappe.db.has_column(DOCTYPE, FIELD):
        # Repair sites where Custom Field metadata was copied but the SQL schema was not.
        frappe.db.updatedb(DOCTYPE)
        action = "synchronized_column"

    if not frappe.db.has_column(DOCTYPE, FIELD):
        frappe.throw("SERVICING OS 7.05: Material Request SQL column was not created")

    return {"status": "OK", "doctype": DOCTYPE, "field": FIELD,
            "options": TARGET, "action": action, "business_records_changed": False}
