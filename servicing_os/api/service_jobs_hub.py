"""Read-only, permission-respecting Service Job register for SERVICING OS.

Mutating actions remain in the already installed lifecycle/workstation/quick_assign
APIs. This module never bypasses a user's document permissions.
"""
import frappe

DT = 'Service Job'
FIELDS = ('name', 'status', 'priority', 'customer_name', 'customer', 'mobile_no',
          'device_type', 'brand', 'device_model', 'serial_number', 'technician',
          'received_date', 'reported_problem', 'modified')
DETAIL_FIELDS = FIELDS + ('estimated_cost', 'actual_delivery', 'accessories_received',
                          'diagnosis', 'remarks')


def _access():
    if frappe.session.user == 'Guest' or not frappe.has_permission(DT, 'read'):
        frappe.throw('Service Job read access is required.', frappe.PermissionError)


def _available(fields):
    meta = frappe.get_meta(DT)
    return [field for field in fields if field in ('name', 'modified') or meta.has_field(field)]


@frappe.whitelist(methods=['GET'])
def get_service_jobs(search='', status='All'):
    _access()
    term = str(search or '').strip()[:90]
    state = str(status or 'All').strip()[:60]
    meta = frappe.get_meta(DT)
    valid = [part.strip() for part in (meta.get_field('status').options or '').splitlines() if part.strip()] if meta.has_field('status') else []
    filters = {}
    if state and state != 'All':
        if state not in valid:
            frappe.throw('Invalid Service Job status filter.')
        filters['status'] = state
    params = {'fields': _available(FIELDS), 'filters': filters,
              'order_by': 'modified desc', 'limit_page_length': 200}
    if term:
        pattern = '%' + term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        choices = [k for k in ('name', 'customer_name', 'brand', 'device_model', 'serial_number')
                   if k == 'name' or meta.has_field(k)]
        params['or_filters'] = [[DT, k, 'like', pattern] for k in choices]
    records = [dict(row) for row in frappe.get_list(DT, **params)]
    for row in records:
        for key in ('modified', 'received_date'):
            if key in row and row[key] is not None:
                row[key] = str(row[key])
    return {'jobs': records, 'status_options': ['All'] + valid,
            'returned': len(records), 'limit': 200,
            'can_create': bool(frappe.has_permission(DT, 'create')),
            'note': 'Only Service Jobs accessible to this login are displayed.'}


@frappe.whitelist(methods=['GET'])
def get_service_job_detail(job_name):
    _access()
    if not job_name or len(str(job_name)) > 140:
        frappe.throw('Select a valid Service Job.')
    doc = frappe.get_doc(DT, job_name)
    if not doc.has_permission('read'):
        frappe.throw('You cannot open this Service Job.', frappe.PermissionError)
    fields = _available(DETAIL_FIELDS)
    detail = {name: doc.get(name) for name in fields}
    for k, v in detail.items():
        if hasattr(v, 'isoformat'):
            detail[k] = str(v)
    return {'job': detail}
