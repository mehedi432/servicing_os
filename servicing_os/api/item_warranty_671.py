"""SERVICING OS 6.71 — Item Master warranty lookup and invoice warranty snapshot.

Item.warranty_period is a Data field containing warranty days in ERPNext v15.
Do not invent warranty type or terms. Previously recorded invoice warranties win.
No direct SQL, commits, stock or accounting changes.
"""
import json
import frappe
from frappe.utils import add_days, getdate
from servicing_os.api.counter_invoice_654 import shop_config

MAX_DAYS = 36500
FIELDS = (
    'custom_sos_warranty_type', 'custom_sos_warranty_period_days',
    'custom_sos_warranty_start_date', 'custom_sos_warranty_expiry_date',
    'custom_sos_warranty_terms',
)


def _days(raw):
    text = str(raw or '').strip()
    if not text or not text.isdigit():
        return 0
    days = int(text)
    return days if 0 < days <= MAX_DAYS else 0


def _item_periods(codes):
    if not codes:
        return {}
    meta = frappe.get_meta('Item')
    if not meta.has_field('warranty_period'):
        return {}
    permitted = frappe.get_list('Item',
        filters={'name': ['in', list(codes)]},
        fields=['name', 'warranty_period'], limit_page_length=min(100, len(codes)))
    return {row.name: _days(row.warranty_period) for row in permitted}


@frappe.whitelist(methods=['GET'])
def get_item_warranties(items=None):
    shop_config()  # existing authenticated, authorized shop/company check
    if not frappe.has_permission('Item', 'read'):
        frappe.throw('Item read permission is required.', frappe.PermissionError)
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except (TypeError, ValueError):
            frappe.throw('Items must be a JSON array.')
    if not isinstance(items, list) or not 1 <= len(items) <= 25:
        frappe.throw('Choose 1–25 Item Codes.')
    codes = [str(x).strip() for x in items]
    if any(not c or len(c) > 140 for c in codes):
        frappe.throw('Invalid Item Code.')
    periods = _item_periods(set(codes))
    return {'items': [{'item_code': c, 'warranty_period_days': periods.get(c, 0),
                       'source': 'ERPNext Item.warranty_period'} for c in codes]}


def populate_invoice_warranty(doc, method=None):
    """Before native submit: snapshot Item warranty days into invoice lines.

    Only operates where 6.59 custom invoice-item warranty fields exist.
    Never overwrites a separately recorded invoice warranty or creates a policy.
    """
    if doc.doctype not in ('Sales Invoice', 'POS Invoice') or int(doc.docstatus or 0) == 2:
        return
    child = doc.doctype + ' Item'
    meta = frappe.get_meta(child)
    if not all(meta.has_field(field) for field in FIELDS):
        return
    codes = set(r.item_code for r in doc.get('items', []) if r.item_code)
    if not codes:
        return
    # Native invoice hooks run with submit permissions. Item access is checked
    # for the logged-in user; no ignore_permissions flag is used.
    if not frappe.has_permission('Item', 'read'):
        return
    days_map = _item_periods(codes)
    posting_date = getdate(doc.posting_date) if doc.get('posting_date') else None
    for row in doc.get('items', []):
        if not row.item_code:
            continue

        # SERVICING_OS_WARRANTY_672: explicit manual/master durations receive
        # correct invoice posting-date start and expiry on native submit.
        recorded_days=_days(row.get('custom_sos_warranty_period_days'))
        if recorded_days:
            if posting_date and not row.get('custom_sos_warranty_start_date'):
                row.set('custom_sos_warranty_start_date',posting_date)
            if row.get('custom_sos_warranty_start_date') and not row.get('custom_sos_warranty_expiry_date'):
                row.set('custom_sos_warranty_expiry_date',add_days(row.get('custom_sos_warranty_start_date'),recorded_days))
            continue
        if any(row.get(field) for field in FIELDS):
            continue  # an explicit warranty or "No Warranty" always wins
        days = days_map.get(row.item_code) or 0
        if not days:
            continue
        row.set('custom_sos_warranty_period_days', days)
        if posting_date:
            row.set('custom_sos_warranty_start_date', posting_date)
            row.set('custom_sos_warranty_expiry_date', add_days(posting_date, days))
        # Do not classify this as Manufacturer/Shop Warranty without source data.
