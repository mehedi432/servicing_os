"""Permission-checked Counter edit/delete endpoints for Service Job (Frappe v15).

Never bypasses Frappe's document permission or link validation. Refuses deletion
of invoiced, processed, non-Received, or changed-since-loaded jobs.
"""
import json
import frappe
from frappe import _
from frappe.utils import flt

ALLOWED = ('customer', 'customer_name', 'mobile', 'device_type', 'brand',
           'device_model', 'serial_number', 'reported_problem',
           'accessories_received', 'priority', 'estimated_cost')
FINAL_STATUSES = {'Delivered', 'Cancelled', 'Canceled'}  # SOS_COUNTER_RECEIVE_REPAIR_689: Completed jobs remain editable until delivery


def _job(name, permission):
    if frappe.session.user == 'Guest':
        frappe.throw(_('Please log in to manage Service Jobs'), frappe.PermissionError)
    name = str(name or '').strip()
    if not name or len(name) > 140:
        frappe.throw(_('Invalid Service Job number'))
    doc = frappe.get_doc('Service Job', name)
    doc.check_permission(permission)
    return doc


def _technician_field():
    meta = frappe.get_meta('Service Job')
    for fieldname in ('technician', 'assigned_technician', 'custom_assigned_technician'):
        field = meta.get_field(fieldname)
        if field and field.fieldtype == 'Link' and field.options in ('User', 'Employee'):
            return field
    return None


def _linked_invoice(name):
    """Inspect standard/custom invoice links even when cashier has no accounting rights."""
    for doctype in ('Sales Invoice', 'Sales Invoice Item'):
        if not frappe.db.exists('DocType', doctype):
            continue
        meta = frappe.get_meta(doctype)
        for fieldname in ('service_job', 'custom_service_job'):
            if not meta.has_field(fieldname):
                continue
            filters = {fieldname: name}
            if meta.is_submittable or frappe.db.has_column(doctype, 'docstatus'):
                filters['docstatus'] = ['!=', 2]
            if frappe.db.exists(doctype, filters):
                return True
    return False


def _can_edit(doc):
    return bool(doc.docstatus == 0 and doc.status not in FINAL_STATUSES
                and doc.has_permission('write'))


def _can_delete(doc):
    """Only fresh, unprocessed, unlinked received records may be deleted."""
    if doc.docstatus != 0 or doc.status != 'Received':
        return False, _('Only Received service jobs can be deleted. Completed, delivered, or processed jobs must be retained.')
    if not doc.has_permission('delete'):
        return False, _('You do not have Service Job Delete permission.')
    if _linked_invoice(doc.name):
        return False, _('This job is referenced by an invoice and cannot be deleted.')
    # SOS_COUNTER_RECEIVE_REPAIR_689: prevent loss of linked spare-parts request history.
    mr_meta = frappe.get_meta('Material Request') if frappe.db.exists('DocType', 'Material Request') else None
    if mr_meta and mr_meta.has_field('custom_service_job') and frappe.db.exists('Material Request', {'custom_service_job': doc.name}):
        return False, _('A spare-parts Material Request references this job; deletion is blocked.')
    if doc.get('diagnosis') or doc.get('repair_notes') or doc.get('actual_cost'):
        return False, _('This job already has repair activity; deletion is blocked.')
    return True, ''


def _snapshot(doc):
    result = {field: doc.get(field) for field in ALLOWED if frappe.get_meta('Service Job').has_field(field)}
    field = _technician_field()
    result.update(name=doc.name, status=doc.status, modified=str(doc.modified),
                  technician=(doc.get(field.fieldname) if field else None))
    # SOS_DEVICE_COMPONENTS_694: read all customer-owned component rows.
    from servicing_os.api.received_components_694 import snapshot
    result['custom_received_components'] = snapshot(doc)
    return result


@frappe.whitelist(methods=['GET'])
def get_job(name):
    doc = _job(name, 'read')
    can_delete, delete_reason = _can_delete(doc)
    return {'job': _snapshot(doc), 'can_edit': _can_edit(doc),
            'can_delete': can_delete, 'delete_reason': delete_reason}


def _parse(data):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (TypeError, ValueError):
            frappe.throw(_('Invalid service job data'))
    if not isinstance(data, dict):
        frappe.throw(_('Expected service job fields'))
    return data


def _verify_version(doc, modified):
    if not modified or str(doc.modified) != str(modified):
        frappe.throw(_('This Service Job changed after you opened it. Reload before saving or deleting.'))


def _validate_technician(value, field):
    if not value:
        return ''
    name = str(value).strip()
    if len(name) > 140:
        frappe.throw(_('Invalid technician ID'))
    if field.options == 'User':
        account = frappe.db.get_value('User', name, ['enabled', 'user_type'], as_dict=True)
        if not account or not account.enabled or account.user_type != 'System User':
            frappe.throw(_('Choose an enabled technician User'))
    elif field.options == 'Employee':
        if frappe.db.get_value('Employee', name, 'status') != 'Active':
            frappe.throw(_('Choose an active technician Employee'))
    return name


@frappe.whitelist(methods=['POST'])
def save_job(name, data=None, expected_modified=None):
    doc = _job(name, 'write')
    if not _can_edit(doc):
        frappe.throw(_('This job is not editable. Check its status and your permissions.'), frappe.PermissionError)
    _verify_version(doc, expected_modified)
    values = _parse(data)
    for fieldname in ALLOWED:
        if fieldname not in values or not doc.meta.has_field(fieldname):
            continue
        value = values[fieldname]
        if fieldname == 'estimated_cost':
            value = flt(value)
            if value < 0:
                frappe.throw(_('Estimated Cost cannot be negative'))
        elif value is not None and not isinstance(value, str):
            frappe.throw(_('Invalid field value: {}').format(fieldname))
        elif isinstance(value, str):
            value = value.strip()
        doc.set(fieldname, value)
    if not doc.get('customer_name') or not doc.get('mobile') or not doc.get('reported_problem'):
        frappe.throw(_('Customer Name, Mobile, and Reported Problem are required'))
    tech_field = _technician_field()
    if 'technician' in values and tech_field:
        doc.set(tech_field.fieldname, _validate_technician(values['technician'], tech_field))
    # Uses normal Frappe validation, modification audit, and DocType hooks.
    # SOS_DEVICE_COMPONENTS_694: optional for backward-compatible service job edits.
    if 'received_components' in values:
        from servicing_os.api.received_components_694 import apply_to_job
        apply_to_job(doc, values['received_components'])
    doc.save(ignore_permissions=False)
    return {'job': _snapshot(doc), 'can_edit': _can_edit(doc), 'can_delete': _can_delete(doc)[0]}


@frappe.whitelist(methods=['POST'])
def delete_job(name, confirm=None, expected_modified=None):
    doc = _job(name, 'delete')
    _verify_version(doc, expected_modified)
    if str(confirm or '') != doc.name:
        frappe.throw(_('Type the exact Service Job number to confirm deletion'))
    allowed, reason = _can_delete(doc)
    if not allowed:
        frappe.throw(reason)
    # Frappe checks all inbound links and executes on_trash hooks. No force or ignore.
    frappe.delete_doc('Service Job', doc.name, ignore_permissions=False, force=False)
    return {'deleted': True, 'name': name}
