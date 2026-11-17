"""SOS_REPAIR_RECORD_ACTIONS_699 — SERVICING OS 6.99 — narrowly scoped edits and guarded permanent Service Job deletion.

This module uses normal Frappe document permissions; never ignore_permissions,
ignore_links, force, or direct SQL deletion. Financial/delivered jobs are protected.
"""
import json
import math

import frappe
from frappe.utils import flt

DT = 'Service Job'
# Existing persisted job values only. Technician, status, customer master, stock,
# and billing are deliberately managed by their original workflows.
EDITABLE = (
    'customer_name', 'mobile', 'mobile_no', 'device_type', 'brand',
    'device_model', 'serial_number', 'priority', 'reported_problem',
    'accessories_received', 'estimated_cost', 'remarks', 'diagnosis',
)
FIELD_TYPES = {'Data', 'Select', 'Small Text', 'Text', 'Long Text', 'Currency', 'Float', 'Int'}
# Explicitly scan non-Link invoice reference fields too (Frappe checks Link fields).
FINANCE_DT = ('Sales Invoice', 'Sales Invoice Item', 'POS Invoice', 'POS Invoice Item',
              'Payment Entry', 'Payment Entry Reference', 'Service Invoice',
              'Service Job Invoice', 'Service Payment', 'Service Delivery')
FINANCE_FIELDS = ('service_job', 'custom_service_job', 'service_job_name',
                  'custom_service_job_name', 'service_job_id', 'custom_service_job_id',
                  'repair_job', 'custom_repair_job', 'job_reference', 'custom_job_reference')
INVOICE_FIELDS_ON_JOB = ('sales_invoice', 'custom_sales_invoice', 'invoice',
                         'invoice_name', 'service_invoice', 'custom_service_invoice',
                         'linked_invoice', 'custom_linked_invoice')


def _doc(name, perm='read'):
    if frappe.session.user == 'Guest':
        frappe.throw('Please sign in to SERVICING OS.', frappe.PermissionError)
    name = str(name or '').strip()
    if not name or len(name) > 140:
        frappe.throw('Select a valid Service Job.')
    if not frappe.db.exists(DT, name):
        frappe.throw('Service Job not found.', frappe.DoesNotExistError)
    doc = frappe.get_doc(DT, name)
    if not doc.has_permission(perm):
        frappe.throw('Service Job {} permission is required.'.format(perm), frappe.PermissionError)
    return doc


def _manager():
    return frappe.session.user == 'Administrator' or 'System Manager' in frappe.get_roles(frappe.session.user)


def _fields(doc):
    out = []
    for name in EDITABLE:
        f = doc.meta.get_field(name)
        if not f or f.fieldtype not in FIELD_TYPES or f.read_only or f.hidden:
            continue
        # Avoid exposing fields that the current role cannot access.
        if f.permlevel and not frappe.has_permission(DT, 'write', doc=doc, permlevel=f.permlevel):
            continue
        options = [line.strip() for line in (f.options or '').splitlines() if line.strip()] if f.fieldtype == 'Select' else []
        out.append({'name': name, 'label': f.label or name.replace('_', ' ').title(),
                    'fieldtype': f.fieldtype, 'reqd': bool(f.reqd),
                    'options': options, 'value': doc.get(name)})
    return out


def _financial_dependencies(doc):
    """Conservative explicit invoice scan, in addition to Frappe's native link checks."""
    deps = []
    for field in INVOICE_FIELDS_ON_JOB:
        if doc.meta.has_field(field) and doc.get(field):
            deps.append('Service Job.{} has an invoice reference'.format(field))
    for dt in FINANCE_DT:
        if not frappe.db.exists('DocType', dt):
            continue
        meta = frappe.get_meta(dt)
        for f in FINANCE_FIELDS:
            if not meta.has_field(f):
                continue
            if frappe.db.exists(dt, {f: doc.name}):
                deps.append('{} references this job'.format(dt))
                break
    return deps


def _delete_eligibility(doc):
    if not _manager():
        return False, 'Only Administrator or a System Manager may permanently delete jobs.'
    if not doc.has_permission('delete'):
        return False, 'Your account does not have Delete permission for this Service Job.'
    if getattr(doc, 'docstatus', 0):
        return False, 'Submitted or cancelled documents cannot be permanently deleted here.'
    if doc.get('status') == 'Delivered' or doc.get('actual_delivery'):
        return False, 'Delivered jobs are protected and cannot be permanently deleted.'
    links = _financial_dependencies(doc)
    if links:
        return False, 'Deletion blocked: ' + '; '.join(links[:3]) + '.'
    return True, ''


@frappe.whitelist(methods=['GET'])
def get_record_context(job_name):
    doc = _doc(job_name, 'read')
    allowed, reason = _delete_eligibility(doc)
    return {
        'job_name': doc.name,
        'modified': str(doc.modified),
        'status': doc.get('status'),
        'fields': _fields(doc),
        'can_edit': bool(doc.has_permission('write') and doc.get('status') != 'Delivered'),
        'can_delete': allowed,
        'delete_reason': reason,
    }


def _parse_values(values):
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except (ValueError, TypeError):
            frappe.throw('Invalid edit payload.')
    if not isinstance(values, dict):
        frappe.throw('Edit values must be an object.')
    return values


@frappe.whitelist(methods=['POST'])
def save_job_changes(job_name, expected_modified=None, values=None):
    doc = _doc(job_name, 'write')
    if str(doc.modified) != str(expected_modified or ''):
        frappe.throw('This Service Job changed since you opened it. Refresh and retry.')
    if doc.get('status') == 'Delivered':
        frappe.throw('Delivered jobs are locked. Use the permitted delivery workflow.')
    values = _parse_values(values)
    available = {f['name']: f for f in _fields(doc)}
    if not values or set(values) - set(available):
        frappe.throw('Edit payload contains an empty or unsupported field.')
    changed = []
    for name, val in values.items():
        field = available[name]
        if not isinstance(val, (int, float, str, type(None))):
            frappe.throw('Invalid value for {}.'.format(field['label']))
        kind = field['fieldtype']
        if kind in ('Float', 'Currency', 'Int'):
            if val is None or str(val).strip() == '':
                if field['reqd']:
                    frappe.throw('{} is required.'.format(field['label']))
                value = 0
            else:
                try:
                    value = flt(val) if kind != 'Int' else int(val)
                except (ValueError, TypeError, OverflowError):
                    frappe.throw('{} must be numeric.'.format(field['label']))
                if not math.isfinite(value):
                    frappe.throw('{} must be a finite number.'.format(field['label']))
                if name == 'estimated_cost' and (value < 0 or value > 100000000):
                    frappe.throw('Estimated cost is out of range.')
        else:
            value = str(val or '').strip()
            maximum = 3000 if kind in ('Small Text', 'Text', 'Long Text') else 140
            if len(value) > maximum:
                frappe.throw('{} is too long.'.format(field['label']))
            if field['reqd'] and not value:
                frappe.throw('{} is required.'.format(field['label']))
            if kind == 'Select' and value and value not in field['options']:
                frappe.throw('Invalid option for {}.'.format(field['label']))
        if doc.get(name) != value:
            doc.set(name, value)
            changed.append(name)
    if not changed:
        return {'saved': False, 'job': doc.name, 'modified': str(doc.modified)}
    doc.save()  # standard validation, permissions, versioning and hooks
    return {'saved': True, 'job': doc.name, 'modified': str(doc.modified), 'changed_fields': changed}


@frappe.whitelist(methods=['POST'])
def permanently_delete_job(job_name, expected_modified=None, confirmation=None):
    doc = _doc(job_name, 'delete')
    if not _manager():
        frappe.throw('Only a System Manager or Administrator may delete a job.', frappe.PermissionError)
    if str(confirmation or '') != doc.name:
        frappe.throw('Type the exact Service Job ID to confirm permanent deletion.')
    if str(expected_modified or '') != str(doc.modified):
        frappe.throw('This Service Job has changed. Refresh before deleting it.')
    allowed, reason = _delete_eligibility(doc)
    if not allowed:
        frappe.throw(reason)
    # Frappe itself blocks linked documents and performs standard clean-up.
    # No ignore_links, ignore_permissions, force or direct SQL delete.
    frappe.delete_doc(DT, doc.name, ignore_permissions=False, force=False)
    return {'deleted': True, 'job': doc.name}
