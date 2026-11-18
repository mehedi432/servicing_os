"""SERVICING OS: repeatable site schema initialization.

Runs after a fresh install and after each bench migrate. Each initializer must be
idempotent and must refuse to overwrite incompatible metadata.
"""
import frappe


def ensure_schema():
    """Synchronize app-owned metadata without changing customer business records."""
    from servicing_os.api.received_components_694 import setup as setup_received_components
    if not frappe.db.exists('DocType', 'Service Job'):
        frappe.throw('SERVICING OS: Service Job DocType is missing; cannot initialize schema')
    return setup_received_components()


def verify():
    """Run: bench --site SITE execute servicing_os.deployment.verify"""
    name = 'Service Received Component'
    if not frappe.db.exists('DocType', 'Service Job'):
        frappe.throw('Missing Service Job DocType')
    if not frappe.db.exists('DocType', name):
        frappe.throw('Missing ' + name + ' DocType')
    parent = frappe.get_meta('Service Job')
    f = parent.get_field('custom_received_components')
    if not f or f.fieldtype != 'Table' or f.options != name:
        frappe.throw('Service Job.custom_received_components is missing or incompatible')
    child = frappe.get_meta(name)
    required = (
        'component_type', 'brand', 'model', 'capacity', 'serial_number',
        'qty', 'condition_received', 'remarks'
    )
    if not child.istable or any(not child.has_field(field) for field in required):
        frappe.throw(name + ' is not a compatible child DocType')
    return {
        'status': 'OK',
        'child_doctype': name,
        'table_field': 'custom_received_components',
        'components_fields': len(required),
        'existing_service_jobs': frappe.db.count('Service Job'),
        'note': 'Existing customer/job/invoice data not rewritten by deployment setup',
    }

# BEGIN SOS_PARTS_REQUEST_SCHEMA_705
_sos705_previous_ensure_schema = ensure_schema
def ensure_schema():
    original = _sos705_previous_ensure_schema()
    from servicing_os.parts_request_schema_705 import ensure as _sos705_parts_ensure
    return {"existing_schema": original, "material_request_link": _sos705_parts_ensure()}
# END SOS_PARTS_REQUEST_SCHEMA_705
