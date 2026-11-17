"""SERVICING OS 6.94 — customer-owned components received with a device.

This is an intake custody record, NOT a stock transaction or spare-parts request.
Metadata setup is for bench execute as administrator, not a client endpoint.
"""
import json
import math

import frappe
from frappe import _

CHILD = 'Service Received Component'
FIELD = 'custom_received_components'
TYPES = ('RAM', 'SSD', 'HDD', 'Power Supply', 'Charger', 'Adapter', 'Battery',
         'GPU', 'CPU', 'Motherboard', 'Monitor', 'Keyboard', 'Mouse', 'Cable',
         'Bag', 'Accessory', 'Other')
CONDITIONS = ('Not Tested', 'Working', 'Faulty', 'Damaged', 'Missing Parts', 'Other')


def setup():
    """Run after a site backup: bench --site servicing.local execute ...setup"""
    if not frappe.db.exists('DocType', 'Service Job'):
        frappe.throw(_('Service Job DocType not found'))
    if not frappe.db.exists('DocType', CHILD):
        module = frappe.db.get_value('DocType', 'Service Job', 'module')
        if not module:
            frappe.throw(_('Service Job module missing'))
        fields = [
            dict(fieldname='component_type', label='Component Type', fieldtype='Select',
                 options='\n'.join(TYPES), reqd=1, in_list_view=1),
            dict(fieldname='brand', label='Brand', fieldtype='Data', in_list_view=1),
            dict(fieldname='model', label='Model', fieldtype='Data'),
            dict(fieldname='capacity', label='Capacity / Specification', fieldtype='Data', in_list_view=1),
            dict(fieldname='serial_number', label='Serial Number', fieldtype='Data'),
            dict(fieldname='qty', label='Quantity', fieldtype='Float', default='1', reqd=1, in_list_view=1),
            dict(fieldname='condition_received', label='Condition On Receipt', fieldtype='Select',
                 options='\n'.join(CONDITIONS), default='Not Tested'),
            dict(fieldname='remarks', label='Remarks', fieldtype='Small Text'),
        ]
        doc = frappe.get_doc(dict(doctype='DocType', name=CHILD, module=module,
                                  custom=1, istable=1, fields=fields))
        doc.insert(ignore_permissions=True)
        print('CREATED child DocType:', CHILD)
    else:
        meta = frappe.get_meta(CHILD)
        if not meta.istable or not all(meta.has_field(x) for x in ('component_type', 'brand', 'capacity', 'qty', 'condition_received')):
            frappe.throw(_('Existing {} is incompatible; migration stopped').format(CHILD))
        print('REUSED child DocType:', CHILD)
    parent = frappe.get_meta('Service Job')
    old_field = parent.get_field(FIELD)
    if old_field:
        if old_field.fieldtype != 'Table' or old_field.options != CHILD:
            frappe.throw(_('Existing Service Job field {} conflicts with this migration').format(FIELD))
        print('REUSED Service Job field:', FIELD)
    else:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
        create_custom_field('Service Job', {
            'fieldname': FIELD, 'label': 'Components Received With Device',
            'fieldtype': 'Table', 'options': CHILD,
            'description': 'Customer-owned RAM, SSD, HDD, PSU and accessories at intake; not shop stock',
            'insert_after': 'accessories_received' if parent.has_field('accessories_received') else 'reported_problem',
            'allow_on_submit': 0,
        })
        print('CREATED parent child-table field:', FIELD)
    frappe.clear_cache(doctype='Service Job')
    frappe.clear_cache(doctype=CHILD)
    frappe.db.commit()
    return {'child_doctype': CHILD, 'parent_field': FIELD}


def normalize(rows):
    if rows is None:
        rows = []
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except (TypeError, ValueError):
            frappe.throw(_('Invalid received components JSON'))
    if not isinstance(rows, list) or len(rows) > 60:
        frappe.throw(_('Received components must be a list of at most 60 rows'))
    cleaned = []
    limits = {'component_type': 50, 'brand': 140, 'model': 140, 'capacity': 140,
              'serial_number': 140, 'condition_received': 40, 'remarks': 500}
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            frappe.throw(_('Component row {} must be an object').format(i))
        obj = {}
        for key, max_length in limits.items():
            val = row.get(key, '')
            if val is None:
                val = ''
            if not isinstance(val, (str, int, float)):
                frappe.throw(_('Invalid {} at component row {}').format(key, i))
            val = str(val).strip()
            if len(val) > max_length:
                frappe.throw(_('{} is too long at component row {}').format(key, i))
            obj[key] = val
        if obj['component_type'] not in TYPES:
            frappe.throw(_('Select a valid component type at row {}').format(i))
        if obj['condition_received'] not in CONDITIONS:
            frappe.throw(_('Select a valid received condition at row {}').format(i))
        try:
            qty = float(row.get('qty', 1))
        except (TypeError, ValueError):
            frappe.throw(_('Invalid quantity in component row {}').format(i))
        if not math.isfinite(qty) or qty <= 0 or qty > 1000:
            frappe.throw(_('Quantity must be greater than 0 and at most 1000 (row {})').format(i))
        obj['qty'] = qty
        cleaned.append(obj)
    return cleaned


def apply_to_job(job, rows):
    if not job.meta.has_field(FIELD):
        frappe.throw(_('Components child table is not installed. Run the 6.94 setup first.'))
    job.set(FIELD, normalize(rows))


def snapshot(job):
    return [
        {key: item.get(key) for key in (
            'component_type', 'brand', 'model', 'capacity', 'serial_number',
            'qty', 'condition_received', 'remarks'
        )}
        for item in (job.get(FIELD) or [])
    ]
