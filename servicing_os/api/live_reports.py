"""SERVICING OS business reports, permission-aware and read-only.

Revenue source: submitted Sales Invoice ONLY. This also includes consolidated
POS sessions once they have been posted; independent POS Invoices are intentionally
NOT added so no revenue is double-counted. Cash is submitted Payment Entry
receipts into the configured Cash ledger; do not assume invoice paid in cash.
"""
from __future__ import annotations
import frappe
from datetime import date, timedelta
from frappe.utils import flt
from servicing_os.api.site_company_706 import cash_account, current_company, shop_warehouses

MAX_ROWS = 5000


def _readable(doctype):
    return bool(frappe.db.exists('DocType',doctype) and frappe.has_permission(doctype,'read'))


def _rows(doctype, filters, fields, order_by='modified desc'):
    result = []
    start = 0
    # Page rather than trust the framework's default 20-row list limit.
    while len(result) < MAX_ROWS:
        block = frappe.get_list(doctype, filters=filters, fields=fields,
                                order_by=order_by, limit_start=start,
                                limit_page_length=min(500, MAX_ROWS-len(result)))
        result.extend([dict(r) for r in block])
        if len(block) < min(500, MAX_ROWS-start):
            return result, False
        start += len(block)
    return result, True


def _json_rows(rows):
    return [{k:(str(v) if isinstance(v,(date,)) or hasattr(v,'isoformat') else v)
             for k,v in x.items()} for x in rows]


def _money(v):
    return round(flt(v), 2)


@frappe.whitelist(methods=['GET'])
def get_business_report(from_date=None, to_date=None, cashier=None, warehouse=None):
    if frappe.session.user == 'Guest':
        frappe.throw('Sign in to view business reports.', frappe.PermissionError)
    start = date.fromisoformat(str(from_date)) if from_date else date.today() - timedelta(days=6)
    end = date.fromisoformat(str(to_date)) if to_date else date.today()
    if end < start or (end-start).days > 366:
        frappe.throw('Choose a valid date range up to 366 days.')
    cashier = (str(cashier or '').strip())[:140]
    warehouse = str(warehouse or '').strip()
    if warehouse and warehouse not in shop_warehouses().values():
        frappe.throw('Select a known shop warehouse.')
    out = {'company':current_company(),'currency':'BDT','from_date':str(start),'to_date':str(end),
           'source':'Submitted Sales Invoices, submitted cash Payment Entries, Service Jobs and Bin quantities',
           'cash_account': cash_account(), 'permissions':{},'warnings':[],
           'sales':[],'payments':[],'jobs':[],'stock':[],
           'kpis':{'net_sales':None,'cash_collected':None,'invoice_outstanding':None,
                   'service_received':None,'open_service_jobs':None,'stock_lines':None}}

    if _readable('Sales Invoice'):
        f = {'company':current_company(),'docstatus':1,'posting_date':['between',[str(start),str(end)]]}
        if cashier: f['owner'] = cashier
        rows,partial = _rows('Sales Invoice',f,
            ['name','posting_date','customer','customer_name','owner','grand_total',
             'outstanding_amount','is_return','is_pos','status'], 'posting_date desc, creation desc')
        for row in rows:
            # Sales return grand_total may already be negative; ensure one deduction.
            row['net_amount'] = -abs(_money(row.get('grand_total'))) if row.get('is_return') else _money(row.get('grand_total'))
        out['sales'] = _json_rows(rows)
        out['kpis']['net_sales'] = _money(sum(x['net_amount'] for x in rows))
        out['kpis']['invoice_outstanding'] = _money(sum(_money(x.get('outstanding_amount')) for x in rows))
        out['permissions']['sales'] = True
        if partial: out['warnings'].append('Sales results reached 5,000 records; totals shown are partial. Narrow the date range.')
    else:
        out['permissions']['sales'] = False
        out['warnings'].append('Your login cannot read Sales Invoices. Sales figures are hidden, not zero.')

    if _readable('Payment Entry'):
        if not out['cash_account'] or not frappe.db.exists('Account', {'name': out['cash_account'], 'company': current_company()}):
            out['warnings'].append('Cash account Cash not found. Cash total is unavailable.')
            out['permissions']['payments'] = False
        else:
            f = {'company': current_company(), 'docstatus':1,'payment_type':'Receive',
                 'paid_to': out['cash_account'],'posting_date':['between',[str(start),str(end)]]}
            if cashier: f['owner'] = cashier
            rows,partial = _rows('Payment Entry',f,
                 ['name','posting_date','party','party_name','owner','paid_to',
                  'received_amount','mode_of_payment'], 'posting_date desc, creation desc')
            out['payments'] = _json_rows(rows)
            out['kpis']['cash_collected'] = _money(sum(_money(x.get('received_amount')) for x in rows))
            out['permissions']['payments'] = True
            if partial: out['warnings'].append('Cash results reached 5,000 records; totals shown are partial.')
    else:
        out['permissions']['payments'] = False
        out['warnings'].append('Your login cannot read Payment Entries. Cash collections are hidden, not zero.')

    if _readable('Service Job'):
        f = {'creation':['between',[str(start)+' 00:00:00',str(end)+' 23:59:59']]}
        if cashier: f['owner'] = cashier
        meta = frappe.get_meta('Service Job')
        fields = ['name','creation','owner'] + [c for c in
            ('status','customer_name','brand','device_model','technician','priority') if meta.has_field(c)]
        rows,partial = _rows('Service Job',f, fields, 'creation desc')
        out['jobs'] = _json_rows(rows)
        out['kpis']['service_received'] = len(rows)
        # Open queue is all-time, and intentionally not filtered by received date.
        queue,queue_partial = _rows('Service Job', {}, ['name','status'] if meta.has_field('status') else ['name'], 'creation desc')
        out['kpis']['open_service_jobs'] = sum(
            1 for j in queue if str(j.get('status') or '').lower() not in ('delivered','cancelled','canceled'))
        out['permissions']['jobs'] = True
        if partial or queue_partial: out['warnings'].append('Service Jobs reached 5,000 rows; counts are partial.')
    else:
        out['permissions']['jobs'] = False
        out['warnings'].append('Your login cannot read Service Jobs. Job statistics are hidden.')

    if _readable('Bin'):
        f = {'warehouse': warehouse if warehouse else ['in',list(shop_warehouses().values())]}
        rows,partial = _rows('Bin', f, ['item_code','warehouse','actual_qty','valuation_rate','stock_value'], 'item_code asc')
        out['stock'] = _json_rows(rows)
        out['kpis']['stock_lines'] = len(rows)
        out['permissions']['stock'] = True
        if partial: out['warnings'].append('Stock results reached 5,000 rows; stock listing is partial.')
    else:
        out['permissions']['stock'] = False
        out['warnings'].append('Your login cannot read warehouse balances. Stock figures are hidden.')
    out['notes'] = [
        'Net Sales = submitted Sales Invoices less sales returns. Separate POS Invoice rows are not added.',
        'Cash Collected = submitted cash-receiving Payment Entries, not sales invoices.',
        'Invoice Outstanding = unpaid balances on invoices in the selected date range.',
        'Service received = Service Jobs created in range; Open Jobs = all-time active queue.',
        'Bin stock is actual quantity, not net available after open POS reservations.',
    ]
    return out
