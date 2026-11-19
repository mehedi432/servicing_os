"""SERVICING OS 6.61 — Permission-checked, read-only Service Job invoice explorer.

Explicitly linked Sales/POS Invoices only; supports legacy link field aliases.
No document writes. Never guesses an invoice-job link from a customer's name.
"""
import re

import frappe
from frappe.utils import cint, flt

LINK_FIELDS = (
    'custom_service_job', 'service_job', 'custom_service_job_no',
    'custom_repair_job', 'service_job_number', 'custom_servicing_job', 'servicing_job',
)
DTYPES = ('Sales Invoice', 'POS Invoice')


def linked_job(invoice):
    names = {str(invoice.get(field)).strip() for field in LINK_FIELDS if invoice.get(field)}
    names.discard('')
    if len(names) > 1:
        frappe.throw('This invoice has conflicting Service Job references.')
    return next(iter(names), '')


def active_sale_invoice_names(job_name, company):
    # Include even unreadable matches to prevent duplicate Sales Invoices.
    meta = frappe.get_meta('Sales Invoice')
    filters = [['Sales Invoice', field, '=', job_name] for field in LINK_FIELDS if meta.has_field(field)]
    if not filters:
        frappe.throw('Service Job invoice link is missing. Run bench migrate.')
    return frappe.get_all('Sales Invoice', filters={'company': company, 'docstatus': ['<', 2], 'is_return': 0},
                          or_filters=filters, pluck='name', limit_page_length=2)


def _shop():
    if frappe.session.user == 'Guest':
        frappe.throw('Please sign in to SERVICING OS.', frappe.PermissionError)
    if not frappe.has_permission('Servicing Shop', 'read'):
        frappe.throw('Servicing Shop read permission is required.', frappe.PermissionError)
    rows = frappe.get_list('Servicing Shop', filters={'is_active': 1},
                           fields=['name', 'company'], limit_page_length=10)
    if len(rows) != 1 or not rows[0].get('company'):
        frappe.throw('Configure exactly one active Servicing Shop.', frappe.ValidationError)
    return rows[0]


def _columns(doctype):
    return {df.fieldname for df in frappe.get_meta(doctype).fields}


def _record_link(row, fields):
    for field in fields:
        if row.get(field):
            return str(row[field]).strip()
    return ''


def _linked_invoices(shop, job_name='', max_results=20):
    output = {}
    link_fields_seen = set()
    visible_jobs = {}
    for doctype in DTYPES:
        if not frappe.db.exists('DocType', doctype) or not frappe.has_permission(doctype, 'read'):
            continue
        columns = _columns(doctype)
        fields = [x for x in LINK_FIELDS if x in columns]
        link_fields_seen.update(fields)
        if not fields:
            continue
        wanted = ['name', 'creation', 'posting_date', 'customer', 'currency', 'grand_total',
                  'outstanding_amount', 'status', 'docstatus', 'is_return'] + fields
        selected = [x for x in wanted if x in columns or x in ('name', 'creation', 'docstatus')]
        # One permission-checked query per possible link field. Limit applies to each query
        # before merging; no customer-only correlation or unbounded full-table scans.
        for link in fields:
            filters = {'company': shop.company}
            filters[link] = job_name if job_name else ['is', 'set']
            records = frappe.get_list(doctype, filters=filters, fields=selected,
                                      order_by='creation desc',
                                      limit_page_length=max(60, max_results * 3))
            for doc in records:
                row = dict(doc)
                matched = str(row.get(link) or '').strip()
                if not matched or (job_name and matched != job_name):
                    continue
                if matched not in visible_jobs:
                    visible_jobs[matched] = bool(frappe.get_list(
                        'Service Job', filters={'name': matched, 'shop': shop.name},
                        fields=['name'], limit_page_length=1))
                if not visible_jobs[matched]:
                    continue
                key = (doctype, row['name'])
                if key in output:
                    continue
                status_int = cint(row.get('docstatus'))
                output[key] = {
                    'doctype': doctype, 'name': row['name'],
                    'service_job': matched, 'customer': row.get('customer') or '',
                    'posting_date': str(row.get('posting_date') or ''),
                    'creation': str(row.get('creation') or ''),
                    'currency': row.get('currency') or 'BDT',
                    'grand_total': flt(row.get('grand_total')),
                    'outstanding_amount': flt(row.get('outstanding_amount')) if row.get('outstanding_amount') is not None else None,
                    'docstatus': status_int,
                    'status': 'Cancelled' if status_int == 2 else 'Draft' if status_int == 0 else (row.get('status') or 'Submitted'),
                    'is_return': bool(cint(row.get('is_return'))),
                }
    invoices = sorted(output.values(), key=lambda r: (r['creation'], r['doctype'], r['name']), reverse=True)
    return invoices[:max_results], sorted(link_fields_seen)


def _job(name, shop):
    if not name or len(name) > 140:
        frappe.throw('Choose a valid Service Job ID.')
    job = frappe.get_doc('Service Job', name)
    job.check_permission('read')
    if job.get('shop') != shop.name:
        frappe.throw('This Service Job belongs to another shop.', frappe.PermissionError)
    return {'name': job.name, 'customer': job.get('customer') or '',
            'customer_name': job.get('customer_name') or '',
            'status': job.get('status') or '', 'shop': job.get('shop')}


@frappe.whitelist(methods=['GET'])
def get_job_context(job_name=''):
    """Direct job lookup for old service jobs not in the invoice modal's recent list."""
    shop = _shop()
    result = _job(str(job_name or '').strip(), shop)
    invoices, links = _linked_invoices(shop, result['name'], 20)
    result['invoices'] = invoices
    result['active_invoice'] = next((x for x in invoices if x['docstatus'] != 2 and not x['is_return']), None)
    return result


@frappe.whitelist(methods=['GET'])
def get_service_invoice_hub(job_name='', limit=20):
    """Recent linked service invoices and jobs; no invoice data outside active shop."""
    shop = _shop()
    n = max(1, min(50, cint(limit) or 20))
    if not frappe.has_permission('Service Job', 'read'):
        frappe.throw('Service Job read permission is required.', frappe.PermissionError)
    typed = str(job_name or '').strip()
    selected = _job(typed, shop) if typed else None
    jobs = frappe.get_list('Service Job', filters={'shop': shop.name},
                           fields=['name', 'customer', 'customer_name', 'status'],
                           order_by='creation desc', limit_page_length=70)
    invoices, link_fields = _linked_invoices(shop, typed, n)
    if selected:
        selected['invoices'] = invoices
        selected['active_invoice'] = next((x for x in invoices if x['docstatus'] != 2 and not x['is_return']), None)
    return {'company': shop.company, 'currency': frappe.db.get_value('Company', shop.company, 'default_currency') or 'BDT',
            'jobs': [dict(x) for x in jobs], 'selected_job': selected,
            'invoices': invoices, 'count': len(invoices), 'link_fields': link_fields,
            'can_create': bool(frappe.has_permission('Sales Invoice', 'create')),
            'note': 'Only invoices explicitly linked to Service Jobs are included. Printing never creates a transaction.'}
