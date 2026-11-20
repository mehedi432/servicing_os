# SOS_634_COUNTER_SNAPSHOT — read-only, user-permission-aware Counter dashboard.
# The dashboard never creates invoices, payments, stock, or Service Jobs.
from __future__ import annotations
import frappe
from frappe.utils import flt, today, now_datetime
from servicing_os.api.site_company_706 import cash_account, current_company, current_currency, retail_warehouse, shop_warehouses, used_laptop_warehouse

MAX_ROWS = 5000


def _visible_rows(doctype, filters, fields, order='modified desc'):
    """Permission-filtered paged query. Never silently truncate a KPI."""
    records = []
    offset = 0
    while True:
        rows = frappe.get_list(
            doctype, filters=filters, fields=fields, order_by=order,
            limit_start=offset, limit_page_length=500)
        records.extend(dict(r) for r in rows)
        if len(rows) < 500:
            return records, False
        offset += len(rows)
        if len(records) >= MAX_ROWS:
            # More rows may exist. Don't present a partial count as a full KPI.
            return records, True


def _read_allowed(doctype):
    return bool(frappe.db.exists('DocType', doctype) and frappe.has_permission(doctype, 'read'))


@frappe.whitelist(methods=['GET'])
def get_counter_snapshot():
    if frappe.session.user == 'Guest':
        frappe.throw('Sign in to view Counter figures.', frappe.PermissionError)
    date = today()
    data = {
        'company': current_company(),
        'currency': current_currency(),
        'date': date,
        'as_of': str(now_datetime()),
        'metrics': {
            'sales_total': None,
            'sales_count': None,
            'cash_receipts': None,
            'received_today': None,
            'ready_delivery': None,
            'open_repairs': None,
            'retail_stock_units': None,
            'used_laptop_stock_units': None,
        },
        'warnings': [],
        'recent_sales': [],
        'recent_jobs': [],
        'notes': {
            'sales': 'Submitted Sales Invoices dated today, including returns. Consolidated POS invoices are not added separately.',
            'cash': 'Submitted Cash Payment Entries (Receive) today; excludes direct POS cash not represented by Payment Entries.',
            'jobs': 'Service Jobs by their current status; active jobs exclude Delivered and Cancelled.',
            'stock': 'Ledger on-hand units from Bin; not available-to-promise after pending sales.',
        }
    }
    kpis = data['metrics']
    if _read_allowed('Sales Invoice'):
        fields = ['name', 'posting_date', 'grand_total', 'customer_name']
        rows, partial = _visible_rows(
            'Sales Invoice',
            {'company': current_company(), 'docstatus': 1, 'posting_date': date},
            fields, 'creation desc')
        if not partial:
            # Returns have negative grand_total in the Sales Invoice ledger.
            kpis['sales_total'] = round(sum(flt(r.get('grand_total')) for r in rows), 2)
            kpis['sales_count'] = len(rows)
        else:
            data['warnings'].append('Sales invoices exceed 5,000 rows for today; totals are withheld to avoid showing incomplete figures.')
        data['recent_sales'] = [
            {'name': r['name'], 'customer_name': r.get('customer_name'), 'total': flt(r.get('grand_total'))}
            for r in rows[:5]
        ]
    else:
        data['warnings'].append('This user cannot read Sales Invoices; sales figures are restricted.')

    if _read_allowed('Payment Entry'):
        account = cash_account()
        if account and frappe.db.exists('Account', account):
            rows, partial = _visible_rows(
                'Payment Entry',
                {'company': current_company(), 'docstatus': 1, 'posting_date': date,
                 'payment_type': 'Receive', 'paid_to': account},
                ['name', 'received_amount'], 'creation desc')
            if not partial:
                kpis['cash_receipts'] = round(sum(flt(r.get('received_amount')) for r in rows), 2)
            else:
                data['warnings'].append('Cash entries exceed 5,000 rows today; cash total is withheld.')
        else:
            data['warnings'].append('Cash account does not exist; cash receipts cannot be calculated.')
    else:
        data['warnings'].append('This user cannot read Payment Entries; cash figures are restricted.')

    if _read_allowed('Service Job'):
        meta = frappe.get_meta('Service Job')
        fields = ['name', 'creation']
        if meta.has_field('status'):
            fields.append('status')
        if meta.has_field('customer_name'):
            fields.append('customer_name')
        rows, partial = _visible_rows('Service Job', {}, fields, 'creation desc')
        if not partial:
            kpis['received_today'] = sum(1 for r in rows if str(r.get('creation') or '')[:10] == date)
            if meta.has_field('status'):
                def status(r):
                    return str(r.get('status') or '').strip().lower()
                kpis['ready_delivery'] = sum(1 for r in rows if status(r) in ('ready to deliver', 'ready for delivery'))
                kpis['open_repairs'] = sum(1 for r in rows if status(r) not in ('delivered', 'cancelled', 'canceled'))
            else:
                data['warnings'].append('Service Job status field not found; repair queue numbers are unavailable.')
        else:
            data['warnings'].append('Service Job register exceeds 5,000 rows; full queue counts are withheld.')
        data['recent_jobs'] = [
            {'name': r['name'], 'status': r.get('status'), 'customer_name': r.get('customer_name')}
            for r in rows[:5]
        ]
    else:
        data['warnings'].append('This user cannot read Service Jobs; repair figures are restricted.')

    if _read_allowed('Bin'):
        rows, partial = _visible_rows('Bin', {'warehouse': ['in', list(shop_warehouses().values())]},
                                      ['item_code', 'warehouse', 'actual_qty'], 'warehouse asc')
        if not partial:
            kpis['retail_stock_units'] = round(sum(flt(r.get('actual_qty')) for r in rows
                                                   if r.get('warehouse') == retail_warehouse()), 2)
            kpis['used_laptop_stock_units'] = round(sum(flt(r.get('actual_qty')) for r in rows
                                                        if r.get('warehouse') == used_laptop_warehouse()), 2)
        else:
            data['warnings'].append('Stock register exceeds 5,000 rows; stock totals are withheld.')
    else:
        data['warnings'].append('This user cannot read stock balances; stock figures are restricted.')
    return data
