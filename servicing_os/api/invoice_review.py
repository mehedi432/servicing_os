"""Submit an existing Sales Invoice after the operator reviews its saved data."""
from datetime import date
from decimal import Decimal, InvalidOperation

import frappe
from frappe.utils import cint

from servicing_os.api.invoice_delivery_657 import _shop
from servicing_os.api.invoice_final_709 import finalize_service_invoice
from servicing_os.api.service_invoice_661 import linked_job


def _invoice_name(value):
    name = str(value or '').strip()
    if not name or len(name) > 140:
        frappe.throw('Choose a saved Sales Invoice.')
    return name


def _review_invoice(name):
    name = _invoice_name(name)
    invoice = frappe.get_doc('Sales Invoice', name)
    invoice.check_permission('read')
    shop = _shop(invoice.company)
    if not shop:
        frappe.throw('This invoice does not belong to an active SERVICING OS company.', frappe.PermissionError)
    frappe.get_doc('Servicing Shop', shop).check_permission('read')
    return invoice


@frappe.whitelist(methods=['POST'])
def submit_reviewed_invoice(invoice_name, expected_modified):
    if frappe.session.user == 'Guest':
        frappe.throw('Sign in to submit invoices.', frappe.PermissionError)
    name = _invoice_name(invoice_name)
    if not expected_modified:
        frappe.throw('Open the saved invoice and review it before submitting.')
    invoice = _review_invoice(name)
    if invoice.docstatus == 1:
        return {'invoice': name, 'docstatus': 1, 'already_submitted': True}
    if invoice.docstatus != 0:
        frappe.throw('Only draft Sales Invoices can be submitted.')
    job = linked_job(invoice) if not cint(invoice.get('is_return')) else ''
    if job:
        # The service workflow locks the job first, then the invoice.
        return finalize_service_invoice(job, name, expected_modified=expected_modified)

    locked = frappe.db.sql('SELECT modified, docstatus FROM `tabSales Invoice` WHERE name=%s FOR UPDATE', (name,))
    invoice = _review_invoice(name)
    if locked and locked[0][1] == 1:
        return {'invoice': name, 'docstatus': 1, 'already_submitted': True}
    if (not locked or locked[0][1] != 0 or str(locked[0][0]) != str(expected_modified)
            or invoice.docstatus != 0 or str(invoice.modified) != str(expected_modified)):
        frappe.throw('This invoice changed after review. Reopen it before submitting.')
    if not cint(invoice.get('is_return')) and linked_job(invoice):
        frappe.throw('The Service Job link changed after review. Reopen the invoice.')
    invoice.check_permission('submit')
    invoice.submit()
    if invoice.docstatus != 1:
        frappe.throw('The invoice did not reach Submitted status.')
    return {'invoice': name, 'docstatus': 1, 'already_submitted': False}


def _editable_invoice(invoice_name):
    invoice = _review_invoice(invoice_name)
    invoice.check_permission('write')
    if invoice.docstatus != 0 or cint(invoice.get('is_return')):
        frappe.throw('Only draft Sales Invoices can be edited here.')
    return invoice


def _quantity_locked(row):
    return any(row.get(field) for field in (
        'delivery_note', 'dn_detail', 'serial_no', 'batch_no', 'serial_and_batch_bundle',
    ))


def _decimal_input(value, label, precision, *, minimum=0, maximum=1000000000):
    try:
        number = Decimal(str(value))
        if (not number.is_finite() or not minimum <= number <= maximum
                or number != number.quantize(Decimal(1).scaleb(-precision))):
            raise ValueError
    except (InvalidOperation, TypeError, ValueError):
        frappe.throw(f'Enter a valid {label} with up to {precision} decimal places.')
    return number


@frappe.whitelist(methods=['GET'])
def get_draft_editor(invoice_name):
    doc = _editable_invoice(invoice_name)
    mode = 'percent' if doc.additional_discount_percentage else ('amount' if doc.discount_amount else 'none')
    return {
        'invoice': doc.name, 'currency': doc.currency, 'modified': str(doc.modified),
        'due_date': str(doc.due_date or ''), 'discount_mode': mode,
        'discount_value': doc.additional_discount_percentage if mode == 'percent' else doc.discount_amount,
        'discount_basis': doc.apply_discount_on or 'Grand Total',
        'items': [{'name': row.name, 'item': row.item_name or row.item_code, 'code': row.item_code,
                   'qty': row.qty, 'rate': row.rate, 'quantity_locked': _quantity_locked(row),
                   'qty_precision': row.precision('qty'), 'rate_precision': row.precision('rate')}
                  for row in doc.items],
    }


@frappe.whitelist(methods=['POST'])
def save_reviewed_draft(invoice_name, expected_modified, items, due_date=None,
                        discount_mode='none', discount_value=0, discount_basis='Grand Total'):
    # Compare the reviewed version to the latest locked parent before saving.
    invoice_name = _invoice_name(invoice_name)
    locked = frappe.db.sql('SELECT modified FROM `tabSales Invoice` WHERE name=%s FOR UPDATE',
                           (invoice_name,))
    doc = _editable_invoice(invoice_name)
    if not locked or not expected_modified or str(locked[0][0]) != str(expected_modified) \
            or str(doc.modified) != str(expected_modified):
        frappe.throw('This invoice changed after review. Reload the draft to edit the latest version.')
    if not isinstance(items, list) or len(items) != len(doc.items) or any(not isinstance(row, dict) for row in items):
        frappe.throw('Save the existing invoice rows.')
    fields = {str(entry.get('name') or ''): entry for entry in items}
    if set(fields) != {line.name for line in doc.items}:
        frappe.throw('Invoice lines changed. Reload the draft.')

    for row in doc.items:
        entry = fields[row.name]
        qty = _decimal_input(entry.get('qty'), 'quantity', row.precision('qty'), minimum=0, maximum=100000)
        rate = _decimal_input(entry.get('rate'), 'selling rate', row.precision('rate'))
        if qty <= 0:
            frappe.throw('Quantity must be greater than zero.')
        if _quantity_locked(row) and qty != _decimal_input(row.qty, 'saved quantity', row.precision('qty')):
            frappe.throw('Quantity is locked on a line with a Delivery Note, serial number, or batch.')
        row.qty = float(qty)
        # Keep native price rules, margins and discounts on unchanged rates.
        if rate != _decimal_input(row.rate, 'saved rate', row.precision('rate')):
            row.rate = row.price_list_rate = float(rate)
            row.discount_percentage = row.discount_amount = 0
            row.margin_type = ''
            row.margin_rate_or_amount = row.rate_with_margin = 0

    if discount_mode not in ('none', 'percent', 'amount') or discount_basis not in ('Net Total', 'Grand Total'):
        frappe.throw('Choose a valid additional discount.')
    precision = doc.precision('additional_discount_percentage' if discount_mode == 'percent' else 'discount_amount')
    value = _decimal_input(discount_value, 'additional discount', precision)
    if discount_mode == 'percent' and value >= 100:
        frappe.throw('Additional discount must be below 100%.')
    doc.apply_discount_on = discount_basis
    doc.additional_discount_percentage = float(value) if discount_mode == 'percent' else 0
    doc.discount_amount = float(value) if discount_mode == 'amount' else 0
    if due_date:
        try:
            doc.due_date = str(date.fromisoformat(str(due_date)))
        except ValueError:
            frappe.throw('Enter a valid due date.')
    doc.save()
    if doc.docstatus != 0 or doc.grand_total <= 0:
        frappe.throw('The saved draft must have a positive invoice total.')
    for row in doc.items:
        entry = fields[row.name]
        if (float(entry['rate']) != float(row.rate) or float(entry['qty']) != float(row.qty)):
            frappe.throw('ERPNext pricing or stock rules changed an entered line. Review the saved invoice.')
    return {'invoice': doc.name, 'docstatus': doc.docstatus, 'modified': str(doc.modified)}
