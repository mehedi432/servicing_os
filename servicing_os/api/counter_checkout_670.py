"""SERVICING OS 6.70: draft editing and authorized one-screen Sales Invoice checkout.

Only an invoice produced by the SERVICING OS unified invoice flow can be
modified/submitted here. Native ERPNext permissions, stock, serial/batch,
accounting, payments, taxation, and Sales Invoice validations are required.
No forced stock ledger updates, permission bypasses, manual GL writes, or commits.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import frappe
from servicing_os.api.counter_invoice_654 import shop_config

SOURCE_PREFIX = 'SERVICING OS |'
D2 = Decimal('0.01')


def _money(value, label, minimum=Decimal('0'), maximum=Decimal('100000000')):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        frappe.throw('Enter a valid ' + label + '.')
    if not result.is_finite() or result < minimum or result > maximum or result.as_tuple().exponent < -2:
        frappe.throw('Invalid ' + label + ': use a positive amount with at most 2 decimal places.')
    return result


def _invoice(invoice_name, permission='read', write_action=False):
    shop = shop_config()
    name = str(invoice_name or '').strip()
    if not name or len(name) > 140:
        frappe.throw('Choose a saved invoice number.')
    doc = frappe.get_doc('Sales Invoice', name)
    doc.check_permission(permission)
    if doc.company != shop.company:
        frappe.throw('Invoice belongs to a different company.', frappe.PermissionError)
    if write_action and not str(doc.get('remarks') or '').startswith(SOURCE_PREFIX):
        frappe.throw('Only invoices created by SERVICING OS can be completed here. Use the original ERPNext workflow.')
    if int(doc.get('is_return') or 0):
        frappe.throw('Returns must use the authorized Sales Return workflow.')
    return doc, shop


def _response(doc):
    kind = 'service' if doc.get('custom_service_job') else ('used' if 'USED LAPTOP' in str(doc.remarks or '') else 'retail')
    return {
        'invoice': doc.name, 'status': doc.status, 'docstatus': doc.docstatus,
        'customer': doc.customer, 'company': doc.company, 'currency': doc.currency,
        'invoice_kind': kind, 'service_job': doc.get('custom_service_job'),
        'update_stock': bool(doc.update_stock), 'is_pos': bool(doc.is_pos),
        'grand_total': float(doc.grand_total or 0), 'net_total': float(doc.net_total or 0),
        'outstanding_amount': float(doc.outstanding_amount or 0),
        'paid_amount': float(doc.paid_amount or 0),
        'discount_mode': 'percent' if float(doc.additional_discount_percentage or 0) else ('amount' if float(doc.discount_amount or 0) else 'none'),
        'discount_value': float(doc.additional_discount_percentage or 0) if float(doc.additional_discount_percentage or 0) else float(doc.discount_amount or 0),
        'items': [{
            'name': r.name, 'item_code': r.item_code,
            'item_name': r.item_name, 'qty': float(r.qty or 0),
            'price_list_rate': float(r.price_list_rate or 0),
            'rate': float(r.rate or 0),
            'discount_percentage': float(r.discount_percentage or 0),
            'warehouse': r.warehouse, 'serial_no': r.serial_no,
            'amount': float(r.amount or 0)
        } for r in doc.items],
        'can_edit': int(doc.docstatus) == 0,
        'can_complete': int(doc.docstatus) == 0,
    }


@frappe.whitelist(methods=['GET'])
def get_checkout(invoice_name=None):
    doc, _ = _invoice(invoice_name, 'read')
    return _response(doc)


@frappe.whitelist(methods=['POST'])
def edit_draft(invoice_name=None, items=None, discount_mode='none', discount_value=0):
    doc, _ = _invoice(invoice_name, 'write', True)
    if doc.docstatus != 0:
        frappe.throw('Submitted invoices cannot be edited. Use Cancel & Amend or Sales Return as permitted.')
    if isinstance(items, str):
        items = frappe.parse_json(items)
    if not isinstance(items, list) or len(items) != len(doc.items):
        frappe.throw('The draft must contain the same item rows. Create a new invoice to add/remove different Items.')
    provided = {str(i.get('name') or ''): i for i in items if isinstance(i, dict)}
    if len(provided) != len(doc.items):
        frappe.throw('Duplicate or unknown invoice rows.')
    for row in doc.items:
        data = provided.get(row.name)
        if data is None:
            frappe.throw('Invoice item changed during editing. Refresh and try again.')
        qty = _money(data.get('qty'), 'quantity', Decimal('0.01'), Decimal('10000'))
        base_rate = _money(data.get('rate'), 'unit selling price')
        pct = _money(data.get('discount_percentage') or 0, 'line discount %', maximum=Decimal('100'))
        # Input rate is the un-discounted unit rate; do not discount it twice.
        price_after_discount = (base_rate * (Decimal('100') - pct) / Decimal('100')).quantize(D2, ROUND_HALF_UP)
        row.qty = float(qty)
        row.price_list_rate = float(base_rate)
        row.discount_percentage = float(pct)
        row.discount_amount = float(base_rate-price_after_discount)
        row.rate = float(price_after_discount)
        if row.get('serial_no'):
            serials = [v.strip() for v in str(row.serial_no).replace(',', '\n').splitlines() if v.strip()]
            if qty != int(qty) or len(serials) != int(qty):
                frappe.throw('Serial number count must match new quantity for ' + row.item_code)
    mode = str(discount_mode or 'none').strip().lower()
    amount = _money(discount_value or 0, 'additional discount')
    if mode not in ('none','percent','amount'):
        frappe.throw('Invalid discount selection.')
    if mode == 'percent' and amount >= 100:
        frappe.throw('Percentage discount must be less than 100%.')
    doc.apply_discount_on = 'Net Total'
    doc.additional_discount_percentage = float(amount) if mode == 'percent' else 0
    doc.discount_amount = float(amount) if mode == 'amount' else 0
    if mode == 'none' and amount:
        frappe.throw('Select a discount mode before entering an amount.')
    doc.save()  # native permissions, stock configuration, totals and tax validation
    if float(doc.grand_total or 0) <= 0:
        frappe.throw('The invoice total must be positive.')
    return _response(doc)


def _cash_account(company):
    if not frappe.db.exists('Mode of Payment', 'Cash'):
        frappe.throw('Configure a Cash Mode of Payment in ERPNext first.')
    mop = frappe.get_doc('Mode of Payment','Cash')
    if getattr(mop,'enabled',1) == 0:
        frappe.throw('Enable the Cash Mode of Payment in ERPNext.')
    matches = [r.default_account for r in mop.accounts if r.company == company and r.default_account]
    if len(matches) != 1:
        frappe.throw('Configure one default Cash account for this company under Mode of Payment → Cash → Accounts.')
    account = frappe.db.get_value('Account',matches[0],['company','is_group','disabled','account_type'],as_dict=True)
    if not account or account.company != company or account.is_group or account.disabled or account.account_type not in ('Cash','Bank'):
        frappe.throw('The Cash Mode of Payment account is not an active Cash/Bank ledger for this company.')
    return matches[0]


@frappe.whitelist(methods=['POST'])
def complete_sale(invoice_name=None, payment_mode='cash', cash_received=None):
    """Submit existing draft; native ERPNext posts stock/accounting/payment in one request.

    Returning an already-submitted invoice is idempotent; no second sale is made.
    """
    doc, shop = _invoice(invoice_name, 'read', True)
    frappe.db.sql('SELECT name FROM `tabSales Invoice` WHERE name=%s FOR UPDATE', (doc.name,))
    doc.reload()
    if doc.docstatus == 1:
        result = _response(doc)
        result.update({'already_completed': True, 'stock_posted': bool(doc.update_stock)})
        return result
    if doc.docstatus != 0:
        frappe.throw('Cancelled invoice cannot be completed.')
    doc.check_permission('submit')
    if not doc.items:
        frappe.throw('Add at least one item to this invoice.')
    stock_items = []
    for row in doc.items:
        if not (row.qty and float(row.qty) > 0):
            frappe.throw('Invalid quantity for ' + row.item_code)
        tracked = bool(frappe.db.get_value('Item',row.item_code,'is_stock_item'))
        if tracked:
            stock_items.append(row)
            if not row.warehouse:
                frappe.throw('Set a warehouse for stock Item ' + row.item_code)
            parent_company = frappe.db.get_value('Warehouse',row.warehouse,'company')
            if parent_company != shop.company:
                frappe.throw('Item warehouse is not part of the shop company: ' + row.warehouse)
    # This flow never creates a Delivery Note. Native Sales Invoice Update Stock
    # posts the outgoing stock ledger when submitted. It must not be used on
    # previously delivered documents, which should follow standard ERPNext flow.
    doc.update_stock = 1 if stock_items else 0
    method = str(payment_mode or 'cash').lower().strip()
    if method not in ('cash','credit'):
        frappe.throw('Choose Cash Received or Pay Later.')
    change = Decimal('0')
    if method == 'cash':
        tendered = _money(cash_received, 'cash received')
        due = _money(doc.grand_total,'invoice total',Decimal('0.01'))
        if tendered < due:
            frappe.throw('Cash received is less than the invoice total.')
        change = tendered - due
        account = _cash_account(shop.company)
        doc.is_pos = 1
        doc.set('payments',[])
        doc.append('payments', {'mode_of_payment':'Cash', 'account':account, 'amount':float(due)})
    else:
        doc.is_pos = 0
        doc.set('payments',[])
    doc.save()  # native validation, including POS payment account
    if method == 'cash':
        actual = _money(doc.grand_total,'final ERPNext invoice total',Decimal('0.01'))
        if tendered < actual:
            frappe.throw('ERPNext recalculated a higher total. Refresh the checkout and collect the correct amount.')
        if abs(Decimal(str(doc.payments[0].amount or 0))-actual) > D2/2:
            doc.payments[0].amount = float(actual)
            doc.save()
        change = tendered - actual
    doc.submit()  # native stock + GL posting (or native failure and rollback)
    if doc.docstatus != 1:
        frappe.throw('Invoice did not reach Submitted state; transaction rolled back.')
    result = _response(doc)
    result.update({'success':True, 'already_completed':False,
                   'stock_posted':bool(doc.update_stock), 'change_due':float(change),
                   'payment_mode':method,
                   'message':'Invoice submitted by ERPNext. Check the stock ledger and payment entry values on the posted invoice.'})
    return result
