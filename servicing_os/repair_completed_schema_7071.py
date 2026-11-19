"""SERVICING OS V7.07.1: make Completed a valid Service Job status.

Applies an idempotent Frappe Property Setter; no Service Job records are changed.
"""
import frappe


def ensure():
    """Called on fresh install and after each bench migrate."""
    from servicing_os.api.repair_progress import setup_completed_option
    return setup_completed_option()


def verify():
    """Read-only: bench --site SITE execute servicing_os.repair_completed_schema_7071.verify"""
    meta = frappe.get_meta("Service Job", cached=False)
    field = meta.get_field("status")
    if not field or field.fieldtype != "Select":
        frappe.throw("Service Job.status must be a Select field")
    options = [s.strip() for s in (field.options or "").splitlines() if s.strip()]
    if "Completed" not in options:
        frappe.throw("Completed missing from Service Job.status options")
    return {"status": "OK", "doctype": "Service Job", "field": "status", "options": options}
