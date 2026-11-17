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
    """Set the Service Job technician before job.insert() in the receive transaction.

    A Service Job Link/User stores the User.name directly; no Employee record needed.
    Existing Link/Employee sites remain supported without modifying their schema.
    """
    # SOS_TECHNICIAN_LINK_USER_685
    selected = str(employee_name or '').strip()
    if not selected:
        return
    if len(selected) > 140:
        frappe.throw(_('Invalid technician identifier'))
    field = _technician_field()
    if not field:
        frappe.throw(_('Technician field is not configured'))
    if field.options == 'User':
        if selected in ('Guest', 'Administrator'):
            frappe.throw(_('Select an enabled technician account'))
        user = frappe.db.get_value('User', selected, ['enabled', 'user_type'], as_dict=True)
        if not user or not user.enabled or user.user_type != 'System User':
            frappe.throw(_('Selected technician is not an enabled System User'))
        job.set(field.fieldname, selected)
        return
    if field.options == 'Employee':
        employee = frappe.db.get_value('Employee', selected, 'status')
        if employee != 'Active':
            frappe.throw(_('Select an active Employee'))
        job.set(field.fieldname, selected)
        return
    frappe.throw(_('Unsupported technician field type'))



@frappe.whitelist(methods=['GET'])
def get_receive_technicians():
    """Minimal technicians directory for staff authorized to receive service jobs."""
    # SOS_TECHNICIAN_LINK_USER_685
    _must_login()
    if not frappe.has_permission('Service Job', 'create'):
        frappe.throw(_('Service Job create permission required'), frappe.PermissionError)
    field = _technician_field()
    if not field:
        return {'technicians': [], 'setup_needed': True, 'field': None}
    if field.options == 'User':
        # This shop's Service Job.technician links User, not Employee.
        # Return only enabled System User identity fields; no emails, phone,
        # roles, HR data or other sensitive profile values.
        users = frappe.get_all('User',
            filters={'enabled': 1, 'user_type': 'System User'},
            fields=['name', 'full_name'], order_by='full_name asc',
            limit_page_length=400)
        people = [
            {'value': user.name, 'label': user.full_name or user.name}
            for user in users
            if user.name not in ('Guest', 'Administrator')
        ]
    elif field.options == 'Employee':
        # Backwards compatibility for sites that genuinely use Link/Employee.
        workers = frappe.get_all('Employee', filters={'status': 'Active'},
            fields=['name', 'employee_name'], order_by='employee_name asc',
            limit_page_length=400)
        people = [
            {'value': person.name, 'label': person.employee_name or person.name}
            for person in workers
        ]
    else:
        frappe.throw(_('Unsupported technician field configuration'))
    return {'technicians': people, 'setup_needed': False,
            'field': field.fieldname, 'source_doctype': field.options,
            'count': len(people)}



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
