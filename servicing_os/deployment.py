"""SERVICING OS: repeatable site schema initialization.

Runs after a fresh install and after each bench migrate. Each initializer must be
idempotent and must refuse to overwrite incompatible metadata.
"""
import frappe


def ensure_schema():
    """Synchronize app-owned metadata without changing customer business records."""
    from servicing_os.api.invoice_warranty_659 import ensure_warranty_fields
    from servicing_os.api.received_components_694 import setup as setup_received_components
    from servicing_os.parts_request_schema_705 import ensure as setup_parts_link
    from servicing_os.parts_request_schema_705 import ensure_service_job_link
    from servicing_os.repair_completed_schema_7071 import ensure as setup_completed_status

    from servicing_os.revenue_streams import ensure_schema as setup_revenue_fields
    from servicing_os.api.invoice_payment import ensure_schema as setup_invoice_payments

    from servicing_os.api.counter_checkout import setup as setup_counter_checkout
    from servicing_os.api.invoice_delivery_657 import ensure_delivery_fields
    from servicing_os.api.sales_center import ensure_warranty_fields as setup_sales_center_warranty
    from servicing_os.api.used_laptop_counter import setup as setup_used_laptops

    if not frappe.db.exists('DocType', 'Service Job'):
        frappe.throw('SERVICING OS: Service Job DocType is missing; cannot initialize schema')
    return {
        'existing_schema': setup_received_components(),
        'material_request_link': setup_parts_link(),
        'completed_status': setup_completed_status(),
        'sales_invoice_link': ensure_service_job_link('Sales Invoice', 'customer'),
        'warranty_fields': ensure_warranty_fields(),
        'revenue_fields': setup_revenue_fields(),
        'invoice_payment_tracking': setup_invoice_payments(),
        'delivery_fields': ensure_delivery_fields(),
        'sales_center_warranty': setup_sales_center_warranty(),
        'retail_checkout': setup_counter_checkout(),
        'used_laptop_fields': setup_used_laptops(),
    }


def verify():
    """Run: bench --site SITE execute servicing_os.deployment.verify"""
    from servicing_os.api.invoice_warranty_659 import ALLOWED, FIELDS
    from servicing_os.parts_request_schema_705 import FIELD, get_service_job_link
    from servicing_os.repair_completed_schema_7071 import verify as verify_completed_status

    from servicing_os.revenue_streams import verify_schema as verify_revenue_fields
    from servicing_os.api.invoice_payment import verify_schema as verify_invoice_payments

    from servicing_os.api.counter_checkout import FIELD as RETAIL_KEY
    from servicing_os.api.used_laptop_counter import FIELDS as LAPTOP_FIELDS, ITEM_PREFIX
    from servicing_os.api.used_laptop_counter import INVOICE_ITEM_FIELD, INVOICE_KEY_FIELD

    extra_fields = {
        'Sales Invoice': (RETAIL_KEY, INVOICE_ITEM_FIELD, INVOICE_KEY_FIELD, 'custom_sos_delivery_status'),
        'Sales Invoice Item': ('custom_sos_warranty_days', 'custom_sos_warranty_expiry'),
        'Item': tuple(ITEM_PREFIX + key for key, *_ in LAPTOP_FIELDS),
    }
    for doctype, fields in extra_fields.items():
        for field in fields:
            if not frappe.db.has_column(doctype, field):
                frappe.throw(f'{doctype}.{field} is missing. Run bench migrate.')

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
    for doctype in ('Material Request', 'Sales Invoice'):
        if not get_service_job_link(doctype) or not frappe.db.has_column(doctype, FIELD):
            frappe.throw(f'{doctype}.{FIELD} is missing. Run bench migrate.')
    for doctype in ALLOWED:
        line_doctype = f'{doctype} Item'
        line_meta = frappe.get_meta(line_doctype, cached=False)
        for fieldname, (fieldtype, _, _) in FIELDS.items():
            field = line_meta.get_field(fieldname)
            if not field or field.fieldtype != fieldtype or not frappe.db.has_column(line_doctype, fieldname):
                frappe.throw(f'{line_doctype}.{fieldname} is missing or incompatible. Run bench migrate.')
    return {
        'status': 'OK',
        'child_doctype': name,
        'table_field': 'custom_received_components',
        'components_fields': len(required),
        'existing_service_jobs': frappe.db.count('Service Job'),
        'material_request_link': True,
        'sales_invoice_link': True,
        'completed_status': verify_completed_status(),
        'warranty_fields': True,
        'revenue_fields': verify_revenue_fields(),
        'invoice_payment_tracking': verify_invoice_payments(),
        'note': 'Existing customer/job/invoice data not rewritten by deployment setup',
    }
