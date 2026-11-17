"""Counter service receive enhancements: technician on intake and paginated history.

Frappe v15. No elevated permissions for client-facing methods.
"""
import frappe
from frappe import _

TECH_FIELDS = (
    'technician', 'assigned_technician', 'custom_assigned_technician',
    'technician_employee', 'service_technician', 'assigned_to_technician',
)


def _technician_field():
    meta = frappe.get_meta('Service Job')
    linked = [f for f in meta.fields if f.fieldtype == 'Link' and f.options in ('Employee', 'User') and not f.read_only]
    for option in ('Employee', 'User'):
        for name in TECH_FIELDS:
            for f in linked:
                if f.fieldname == name and f.options == option:
                    return f
    candidates = [f for f in linked if 'technician' in (f.fieldname or '').lower() or 'technician' in (f.label or '').lower()]
    return candidates[0] if len(candidates) == 1 else None


def ensure_technician_field():
    """Run once with bench execute as site administrator; does not overwrite known fields."""
    field = _technician_field()
    if field:
        print('REUSED Service Job field: {} ({})'.format(field.fieldname, field.options))
        return field.fieldname
    if frappe.db.exists('Custom Field', 'Service Job-custom_assigned_technician'):
        frappe.throw(_('custom_assigned_technician exists but cannot be used; inspect its type/options'))
    meta = frappe.get_meta('Service Job')
    names = [f.fieldname for f in meta.fields if f.fieldname]
    insert_after = 'status' if 'status' in names else ('customer' if 'customer' in names else names[-1] if names else None)
    values = {
        'fieldname': 'custom_assigned_technician',
        'label': 'Assigned Technician',
        'fieldtype': 'Link',
        'options': 'Employee',
        'description': 'Assigned during Service Receive at Counter',
        'in_list_view': 1,
    }
    if insert_after: values['insert_after'] = insert_after
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    create_custom_field('Service Job', values)
    frappe.clear_cache(doctype='Service Job')
    frappe.db.commit()
    print('CREATED Service Job.custom_assigned_technician')
    return 'custom_assigned_technician'


def _must_login():
    if frappe.session.user == 'Guest':
        frappe.throw(_('Please sign in'), frappe.PermissionError)


def assign_technician_on_create(job, employee_name):
    """Use inside receive_service_job, BEFORE job.insert(), in its transaction."""
    name = str(employee_name or '').strip()
    if not name:
        return
    if len(name) > 140:
        frappe.throw(_('Invalid employee identifier'))
    field = _technician_field()
    if not field:
        frappe.throw(_('Technician field is not configured; ask administrator to run setup'))
    # Service Job.create permission is checked by the caller.
    employee = frappe.db.get_value('Employee', name, ['status', 'user_id'], as_dict=True)
    if not employee or employee.status != 'Active':
        frappe.throw(_('Choose an active technician'))
    value = name if field.options == 'Employee' else employee.user_id
    if not value:
        frappe.throw(_('This technician has no linked User account'))
    job.set(field.fieldname, value)


@frappe.whitelist(methods=['GET'])
def get_receive_technicians():
    _must_login()
    if not frappe.has_permission('Service Job', 'create'):
        frappe.throw(_('Service Job create permission required'), frappe.PermissionError)
    field = _technician_field()
    if not field:
        return {'technicians': [], 'setup_needed': True, 'field': None}
    # SOS_RECEIVE_PRINT_STUDIO_683: a minimal technician chooser for POS staff.
    # Service Job Create is the authorization gate above. Do not expose HR data,
    # payroll, mobile, addresses, DOB, or other Employee fields. Name and Employee ID
    # are the minimum information needed to select an assignee. Frappe's get_all
    # is deliberate here because counter users often lack HR/Employee Read access.
    fields = ['name', 'employee_name', 'user_id']
    workers = frappe.get_all('Employee', filters={'status': 'Active'}, fields=fields,
                              order_by='employee_name asc', limit_page_length=400)
    people = []
    for person in workers:
        if field.options == 'User' and not person.user_id:
            continue
        people.append({'value': person.name, 'label': '{} · {}'.format(person.employee_name or person.name, person.name)})
    return {'technicians': people, 'setup_needed': False, 'field': field.fieldname}


@frappe.whitelist(methods=['GET'])
def get_receive_history(q='', customer='', page=1):
    """Return exactly five permitted Service Jobs/page, or five for selected customer."""
    _must_login()
    if not frappe.has_permission('Service Job', 'read'):
        frappe.throw(_('Service Job read permission required'), frappe.PermissionError)
    try: page = max(1, min(10000, int(page)))
    except (TypeError, ValueError): page = 1
    query = str(q or '').strip()[:90]
    selected_customer = str(customer or '').strip()[:140]
    filters = {}
    or_filters = None
    # Searching across ALL jobs overrides selected-customer history filtering.
    if query:
        pattern = '%' + query + '%'
        or_filters = [
            ['Service Job', 'name', 'like', pattern],
            ['Service Job', 'customer_name', 'like', pattern],
            ['Service Job', 'mobile', 'like', pattern],
            ['Service Job', 'serial_number', 'like', pattern],
        ]
    elif selected_customer:
        filters['customer'] = selected_customer
    # Never bypass record-level permissions: get_list, not get_all.
    rows = frappe.get_list(
        'Service Job', fields=['name', 'customer_name', 'mobile', 'device_type',
                               'brand', 'device_model', 'status', 'received_date'],
        filters=filters, or_filters=or_filters, order_by='creation desc',
        limit_start=(page - 1)*5, limit_page_length=6,
    )
    return {
        'jobs': [dict(row) for row in rows[:5]],
        'page': page,
        'has_next': len(rows) > 5,
        'has_prev': page > 1,
        'page_size': 5,
    }
