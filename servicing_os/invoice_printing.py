"""Shared read-only fields for SERVICING OS invoice and receipt printing."""

import frappe
from frappe.utils import flt


def invoice_serial_numbers(invoice, lines):
    """Resolve only stock bundles posted for this invoice and its exact lines."""
    sources = {row.get('serial_and_batch_bundle'): row for row in lines if row.get('serial_and_batch_bundle')}
    if not sources:
        return {}
    bundles = frappe.get_all('Serial and Batch Bundle', filters={
        'name': ['in', list(sources)], 'voucher_type': invoice.doctype,
        'voucher_no': invoice.name, 'company': invoice.company,
    }, fields=['name', 'voucher_detail_no', 'item_code'])
    verified = {bundle.name: sources[bundle.name].name for bundle in bundles
                if sources[bundle.name].name == bundle.voucher_detail_no
                and sources[bundle.name].item_code == bundle.item_code}
    if not verified:
        return {}
    serials = {}
    for entry in frappe.get_all('Serial and Batch Entry', filters={
        'parenttype': 'Serial and Batch Bundle', 'parent': ['in', list(verified)],
    }, fields=['parent', 'serial_no'], order_by='idx asc'):
        if entry.serial_no:
            serials.setdefault(verified[entry.parent], []).append(entry.serial_no)
    return {row: '\n'.join(dict.fromkeys(values)) for row, values in serials.items()}


def invoice_amount_for_print(grand_total, currency, *, rounding_adjustment=0):
    """Spell the same payable amount that the print template displays."""
    from frappe.utils import money_in_words

    adjustment = flt(rounding_adjustment, 2)
    amount = flt(flt(grand_total, 2) + adjustment, 2)
    words = money_in_words(abs(amount), currency, 'Paisa' if currency == 'BDT' else None)
    return {
        'print_total': amount,
        'print_rounding_adjustment': adjustment,
        'amount_in_words': ('Minus ' if amount < 0 else '') + words,
    }


def invoice_document_print_amounts(invoice, currency):
    grand_total = invoice.get('grand_total')
    adjustment = flt(invoice.get('rounding_adjustment'), 2)
    rounded = invoice.get('rounded_total')
    if (invoice.get('disable_rounded_total') or rounded is None
            or flt(flt(grand_total, 2) + adjustment, 2) != flt(rounded, 2)):
        adjustment = 0
    return invoice_amount_for_print(grand_total, currency, rounding_adjustment=adjustment)


def invoice_payment_schedule(invoice):
    return [
        {'label': row.get('payment_term') or '', 'due_date': str(row.get('due_date') or ''),
         'amount': flt(row.get('payment_amount'))}
        for row in invoice.get('payment_schedule') or []
        if row.get('due_date')
    ]
