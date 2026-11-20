"""SERVICING OS - read-only Sales and Profit & Loss period comparison.

Sales: submitted Sales Invoice base_net_total excluding sales taxes, returns negative.
P&L: posted GL Entry debit/credit in company base currency; profit = all P&L
income less P&L expense. Period Closing Vouchers and cancelled GL are excluded.
Permissions are enforced by Frappe get_list (including user permissions).
"""
from collections import defaultdict
from datetime import date, timedelta
import calendar

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
from servicing_os.api.site_company_706 import current_company

PERIODS = {"daily": 366, "weekly": 156, "monthly": 60, "yearly": 10}
PAGE_SIZE = 750
MAX_INVOICES = 30000
MAX_GL = 60000


def _need(doctype):
    if frappe.session.user == 'Guest' or not frappe.has_permission(doctype, 'read'):
        frappe.throw(_("Insufficient permissions for {0}.").format(doctype), frappe.PermissionError)


def _pages(doctype, filters, fields, ceiling):
    """Do not bypass row-level permission conditions or return truncated numbers."""
    start = 0
    while True:
        chunk = frappe.get_list(doctype, filters=filters, fields=fields,
                                start=start, page_length=PAGE_SIZE,
                                order_by="name asc")
        for row in chunk:
            yield row
        start += len(chunk)
        if len(chunk) < PAGE_SIZE:
            return
        if start >= ceiling:
            frappe.throw(_("Too many financial records for the quick report. Use native ERPNext financial reports for this date range."))


def _bounds(granularity, start, end):
    if bool(start) != bool(end):
        frappe.throw(_("Choose both start and end dates, or leave both blank."))
    now = getdate(nowdate())
    if start and end:
        first, last = getdate(start), getdate(end)
    else:
        last = now
        if granularity == 'daily':
            first = last - timedelta(days=29)
        elif granularity == 'weekly':
            first = last - timedelta(days=last.weekday() + 7 * 11)
        elif granularity == 'monthly':
            year, month = last.year, last.month - 11
            while month <= 0:
                month += 12
                year -= 1
            first = date(year, month, 1)
        else:
            first = date(last.year - 4, 1, 1)
    if first > last or last > now + timedelta(days=1):
        frappe.throw(_("Invalid reporting range."))
    def bucket(d):
        if granularity == 'daily':
            return d
        if granularity == 'weekly':
            return d - timedelta(days=d.weekday())
        if granularity == 'monthly':
            return date(d.year, d.month, 1)
        return date(d.year, 1, 1)
    a, b = bucket(first), bucket(last)
    if granularity == 'daily':
        n = (b-a).days + 1
    elif granularity == 'weekly':
        n = (b-a).days // 7 + 1
    elif granularity == 'monthly':
        n = (b.year-a.year)*12 + b.month-a.month + 1
    else:
        n = b.year-a.year+1
    if n > PERIODS[granularity]:
        frappe.throw(_("Maximum {0} {1} periods at a time.").format(PERIODS[granularity], granularity))
    return first, last, bucket, a, b


def _pkey(d, kind):
    if kind == 'daily':
        return d
    if kind == 'weekly':
        return d-timedelta(days=d.weekday())
    if kind == 'monthly':
        return date(d.year,d.month,1)
    return date(d.year,1,1)


def _period_label(d, kind):
    if kind == 'daily':
        return d.strftime('%d %b %Y')
    if kind == 'weekly':
        iso = d.isocalendar()
        return f'W{iso.week:02d} · {iso.year} ({d:%d %b}–{(d + timedelta(days=6)):%d %b})'
    if kind == 'monthly':
        return d.strftime('%b %Y')
    return str(d.year)


def _empty():
    return dict(sales=0.0, returns=0.0, net_sales=0.0, invoice_count=0,
                pnl_income=0.0, cogs=0.0, expenses=0.0, operating_expenses=0.0,
                gross_profit=None, net_profit=None, margin_pct=None)


def _round(row, pnl):
    if pnl:
        row['operating_expenses'] = row['expenses'] - row['cogs']
        row['gross_profit'] = row['net_sales'] - row['cogs']
        row['net_profit'] = row['pnl_income'] - row['expenses']
        row['margin_pct'] = (100 * row['net_profit'] / row['net_sales']) if row['net_sales'] > 0 else None
    for key in ('sales', 'returns', 'net_sales', 'pnl_income', 'cogs', 'expenses',
                'operating_expenses', 'gross_profit', 'net_profit', 'margin_pct'):
        if row[key] is not None:
            row[key] = round(row[key], 2)
    return row


@frappe.whitelist(methods=['GET'])
def period_report(granularity='daily', from_date=None, to_date=None):
    """Real permission-aware period rollups, no synthetic revenue or profit figures."""
    _need('Sales Invoice')
    if granularity not in PERIODS:
        frappe.throw(_('Invalid period.'))
    if not frappe.has_permission('Company', 'read', current_company()):
        frappe.throw(_('You cannot report on this company.'), frappe.PermissionError)
    first, last, bucket, from_bucket, to_bucket = _bounds(granularity, from_date, to_date)
    records = defaultdict(_empty)
    # Submitted invoice base currency amount is net of taxes; return totals are negative.
    inv_count = 0
    for inv in _pages('Sales Invoice', {'company': current_company(), 'docstatus': 1,
                  'posting_date': ['between', [str(first), str(last)]]},
                  ['name', 'posting_date', 'base_net_total', 'is_return'], MAX_INVOICES):
        row = records[bucket(getdate(inv.posting_date))]
        amount = flt(inv.base_net_total)
        if inv.is_return:
            row['returns'] += abs(amount)
            row['net_sales'] -= abs(amount)
        else:
            row['sales'] += amount
            row['net_sales'] += amount
            row['invoice_count'] += 1
        inv_count += 1

    # Permission-aware ledger fetch. If Accounts permissions are absent, do not display fake zeros.
    pnl_visible = frappe.has_permission('GL Entry', 'read') and frappe.has_permission('Account', 'read')
    explanation = ''
    gl_count = 0
    if pnl_visible:
        account_lookup = {}
        for acc in _pages('Account', {'company': current_company(), 'is_group': 0},
                          ['name','root_type','account_type','report_type'], 10000):
            if acc.root_type in ('Income','Expense') and acc.report_type == 'Profit and Loss':
                account_lookup[acc.name] = (acc.root_type, acc.account_type)
        if not account_lookup:
            pnl_visible = False
            explanation = 'No accessible Profit and Loss accounts configured.'
        else:
            for gl in _pages('GL Entry', {'company': current_company(),'is_cancelled': 0,
                       'posting_date': ['between', [str(first), str(last)]],
                       'voucher_type': ['!=', 'Period Closing Voucher']},
                       ['name','posting_date','account','debit','credit','is_opening'], MAX_GL):
                account = account_lookup.get(gl.account)
                if not account or gl.is_opening == 'Yes':
                    continue
                root, account_type = account
                row = records[bucket(getdate(gl.posting_date))]
                if root == 'Income':
                    row['pnl_income'] += flt(gl.credit) - flt(gl.debit)
                else:
                    amount = flt(gl.debit) - flt(gl.credit)
                    row['expenses'] += amount
                    if account_type == 'Cost of Goods Sold':
                        row['cogs'] += amount
                gl_count += 1
            if gl_count == 0:
                pnl_visible = False
                explanation = 'No posted Profit & Loss journal entries in this date range.'
    else:
        explanation = 'P&L hidden: your role requires both Account and GL Entry read access.'

    periods = []
    cursor = from_bucket
    while cursor <= to_bucket:
        periods.append(cursor)
        if granularity == 'daily':
            cursor += timedelta(days=1)
        elif granularity == 'weekly':
            cursor += timedelta(days=7)
        elif granularity == 'monthly':
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        else:
            cursor = date(cursor.year + 1, 1, 1)
    rows = []
    totals = _empty()
    for d in periods:
        row = dict(records.get(d, _empty()))
        for key in ('sales','returns','net_sales','invoice_count','pnl_income','cogs','expenses'):
            totals[key] += row[key]
        rows.append(dict(period_key=d.isoformat(), label=_period_label(d,granularity),
                         **_round(row,pnl_visible)))
    return {'company': current_company(), 'currency': frappe.db.get_value('Company',current_company(),'default_currency') or 'BDT',
            'granularity': granularity, 'from_date': str(first), 'to_date': str(last),
            'pnl_visible': bool(pnl_visible), 'pnl_note': explanation,
            'totals': _round(totals,pnl_visible), 'rows': list(reversed(rows)),
            'invoice_rows': inv_count, 'pnl_gl_rows': gl_count,
            'basis': 'Submitted Sales Invoice base_net_total (excluding taxes), and posted P&L General Ledger entries. Refunds/credit notes reduce net sales. Net profit includes all posted P&L income and expenses, not only merchandise.'}
