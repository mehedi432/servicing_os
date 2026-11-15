"""SERVICING OS 6.58: permission-checked recent customer Sales/POS invoice register.

Read-only. Does not create, submit, cancel or reprint/duplicate accounting documents.
An invoice 'duplicate copy' is a print designation only.
"""
import frappe
from frappe.utils import cint, flt

ALLOWED_SCOPES = ('all', 'sale', 'repair', 'used')
SERVICE_LINK = 'custom_service_job'


def _company():
    if frappe.session.user == 'Guest':
        frappe.throw('Please sign in to SERVICING OS.', frappe.PermissionError)
    if not frappe.has_permission('Servicing Shop', 'read'):
        frappe.throw('Servicing Shop read permission is required.', frappe.PermissionError)
    shops = frappe.get_list('Servicing Shop',
        filters={'is_active': 1}, fields=['name', 'company'], limit_page_length=10)
    if len(shops) != 1 or not shops[0].get('company'):
        frappe.throw('Configure exactly one active Servicing Shop for this counter.')
    return shops[0].get('company')


def _metadata(dt):
    return {f.fieldname for f in frappe.get_meta(dt).fields}


def _kind(row):
    if row.get(SERVICE_LINK):
        return 'repair'
    remarks = str(row.get('remarks') or '').upper()
    if 'SERVICING OS | SERVICE JOB' in remarks:
        return 'repair'
    if 'SERVICING OS | USED LAPTOP' in remarks:
        return 'used'
    return 'sale'


def _invoices(dt, company, scope, limit, customer):
    if not frappe.db.exists('DocType', dt) or not frappe.has_permission(dt, 'read'):
        return []
    available = _metadata(dt)
    required = {'company', 'customer', 'posting_date', 'grand_total', 'currency'}
    if not required.issubset(available):
        return []
    expected = ['name', 'creation', 'posting_date', 'customer', 'company',
                'currency', 'grand_total', 'docstatus', 'status',
                'outstanding_amount', 'paid_amount', 'remarks', 'is_return',
                SERVICE_LINK, 'custom_sos_delivery_status']
    fields = [f for f in expected if f in available or f in ('name', 'creation', 'docstatus')]
    filters = {'company': company}
    if customer:
        filters['customer'] = customer
    # Repair transactions are explicitly linked in SERVICING OS invoices.
    # Select them at the database, not by cutting off the last 20 retail records.
    if scope == 'repair' and SERVICE_LINK in available:
        filters[SERVICE_LINK] = ['is', 'set']
    if scope == 'used' and 'remarks' in available:
        filters['remarks'] = ['like', '%USED LAPTOP%']
    # Restrict retrieval by Frappe user permissions using get_list (not get_all).
    rows = frappe.get_list(dt, filters=filters, fields=fields,
                           order_by='creation desc', limit_page_length=limit)
    result = []
    for raw in rows:
        row = dict(raw)
        kind = _kind(row)
        if scope == 'repair' and kind != 'repair':
            continue
        if scope == 'used' and kind != 'used':
            continue
        if scope == 'sale' and kind == 'repair':
            continue
        docstatus = cint(row.get('docstatus'))
        status = 'Cancelled' if docstatus == 2 else ('Draft' if docstatus == 0 else (row.get('status') or 'Submitted'))
        result.append({
            'name': row['name'], 'doctype': dt,
            'customer': row.get('customer') or '',
            'posting_date': str(row.get('posting_date') or ''),
            'creation': str(row.get('creation') or ''),
            'currency': row.get('currency') or 'BDT',
            'grand_total': flt(row.get('grand_total')),
            'outstanding_amount': flt(row.get('outstanding_amount')) if row.get('outstanding_amount') is not None else None,
            'docstatus': docstatus, 'status': status,
            'invoice_kind': kind, 'service_job': row.get(SERVICE_LINK) or '',
            'delivery_status': row.get('custom_sos_delivery_status') or '',
            'is_return': bool(cint(row.get('is_return'))),
        })
    return result


@frappe.whitelist(methods=['GET'])
def get_recent_invoices(scope='all', limit=20, customer=''):
    """Last 20 available Sales/POS invoices in active shop, with optional category/customer."""
    scope = str(scope or 'all').lower().strip()
    if scope not in ALLOWED_SCOPES:
        frappe.throw('Invalid invoice history category.')
    n = max(1, min(20, cint(limit) or 20))
    customer = str(customer or '').strip()
    if len(customer) > 140:
        frappe.throw('Customer identifier is too long.')
    company = _company()
    # Enforce a full per-DocType candidate window before merging; makes POS
    # and Sales invoices comparable by creation timestamp.
    per_type = 120 if scope in ('sale', 'repair', 'used') else 40
    data = []
    for dt in ('Sales Invoice', 'POS Invoice'):
        data += _invoices(dt, company, scope, per_type, customer)
    data.sort(key=lambda r: (r['creation'], r['doctype'], r['name']), reverse=True)
    return {
        'company': company, 'scope': scope, 'limit': n,
        'invoices': data[:n], 'count': min(len(data), n),
        'note': 'Read-only history. Duplicate copy printing never creates a second invoice.',
    }
