"""Post an actual receipt against one submitted Sales Invoice."""
import re
from datetime import date
from decimal import Decimal

import frappe
from frappe.utils import cint, nowdate

from servicing_os.api.invoice_review import _decimal_input, _invoice_name, _review_invoice

REQUEST_KEY = 'custom_sos_invoice_payment_key'


def verify_schema():
    field = frappe.get_meta('Payment Entry', cached=False).get_field(REQUEST_KEY)
    if not field or field.fieldtype != 'Data' or not field.unique or not frappe.db.has_column('Payment Entry', REQUEST_KEY):
        frappe.throw('Invoice payment tracking field is missing or incompatible. Run bench migrate.')
    return True


def ensure_schema():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    meta = frappe.get_meta('Payment Entry', cached=False)
    if not meta.has_field(REQUEST_KEY):
        create_custom_fields({'Payment Entry': [{
            'fieldname': REQUEST_KEY, 'label': 'SERVICING OS Invoice Payment Key',
            'fieldtype': 'Data', 'insert_after': 'reference_no', 'unique': 1,
            'read_only': 1, 'hidden': 1, 'no_copy': 1, 'print_hide': 1,
        }]}, update=False)
        frappe.clear_cache(doctype='Payment Entry')
    return verify_schema()


def can_receive():
    return all(frappe.has_permission('Payment Entry', action) for action in ('create', 'submit'))


def _check(invoice):
    if not can_receive():
        frappe.throw('Payment Entry create and submit permissions are required.', frappe.PermissionError)
    if invoice.docstatus != 1 or cint(invoice.get('is_return')):
        frappe.throw('Receive payment against a submitted Sales Invoice.')
    base = frappe.get_cached_value('Company', invoice.company, 'default_currency')
    receivable = frappe.db.get_value('Account', invoice.debit_to, 'account_currency') if invoice.debit_to else None
    if not base or invoice.currency != base or receivable != base:
        frappe.throw('Use ERPNext Payment Entry for foreign-currency invoices or receivables.')
    return base


def _accounts(company, currency):
    modes = frappe.get_all('Mode of Payment', filters={'enabled': 1, 'type': ['in', ['Cash', 'Bank']]},
                           fields=['name', 'type'], order_by='name asc')
    if not modes:
        return {}
    links = frappe.get_all('Mode of Payment Account', filters={
        'parent': ['in', [mode.name for mode in modes]], 'parenttype': 'Mode of Payment', 'company': company,
    }, fields=['parent', 'default_account'])
    accounts = {}
    for mode in modes:
        names = {entry.default_account for entry in links if entry.parent == mode.name and entry.default_account}
        if len(names) != 1:
            continue
        name = next(iter(names))
        ledger = frappe.db.get_value('Account', name, ['company', 'account_type', 'is_group', 'disabled', 'account_currency'],
                                     as_dict=True)
        if (ledger and ledger.company == company and ledger.account_type in ('Cash', 'Bank')
                and not ledger.is_group and not ledger.disabled and ledger.account_currency == currency):
            accounts[mode.name] = {'account': name, 'needs_reference': mode.type == 'Bank' or ledger.account_type == 'Bank'}
    return accounts


def _balance(invoice, value):
    return Decimal(str(value or 0)).quantize(Decimal(1).scaleb(-invoice.precision('outstanding_amount')))


def _matching_references(rows, invoice_name):
    return bool(rows) and all(row.reference_doctype == 'Sales Invoice' and row.reference_name == invoice_name for row in rows)


def _allocate(payment, invoice, amount):
    if len(payment.references) == 1:
        payment.references[0].allocated_amount = float(amount)
        return
    remaining = amount
    for row in list(payment.references):
        capacity = max(Decimal(0), _balance(invoice, row.allocated_amount or row.outstanding_amount))
        allocation = min(capacity, remaining)
        if allocation:
            row.allocated_amount = float(allocation)
            remaining -= allocation
        else:
            payment.remove(row)
    if remaining:
        frappe.throw('The receipt could not be allocated to the invoice payment schedule.')


@frappe.whitelist(methods=['GET'])
def get_payment_context(invoice_name):
    invoice = _review_invoice(invoice_name)
    currency = _check(invoice)
    if invoice.outstanding_amount <= 0:
        frappe.throw('This invoice has no outstanding balance.')
    if not frappe.db.has_column('Payment Entry', REQUEST_KEY):
        frappe.throw('Run bench migrate to enable invoice payment tracking.')
    accounts = _accounts(invoice.company, currency)
    if not accounts:
        frappe.throw('Configure an enabled Cash or Bank Mode of Payment with a company ledger in ERPNext.')
    return {'invoice': invoice.name, 'currency': currency, 'posting_date': nowdate(),
            'outstanding': str(_balance(invoice, invoice.outstanding_amount)),
            'precision': invoice.precision('outstanding_amount'),
            'methods': [{'name': name, **details} for name, details in accounts.items()]}


@frappe.whitelist(methods=['POST'])
def receive_invoice_payment(invoice_name, amount, mode_of_payment, expected_outstanding, request_key,
                            reference_no=None, reference_date=None):
    if not re.fullmatch('[0-9a-f]{32}', str(request_key or '')):
        frappe.throw('Open the payment form to start a new receipt.')
    invoice_name = _invoice_name(invoice_name)
    locked = frappe.db.sql('SELECT outstanding_amount, docstatus FROM `tabSales Invoice` WHERE name=%s FOR UPDATE',
                           (invoice_name,))
    invoice = _review_invoice(invoice_name)
    currency = _check(invoice)
    if not locked or locked[0][1] != 1:
        frappe.throw('Receive payment against a submitted Sales Invoice.')
    if not frappe.db.has_column('Payment Entry', REQUEST_KEY):
        frappe.throw('Invoice payment tracking is unavailable. Run bench migrate.')
    precision = invoice.precision('outstanding_amount')
    amount = _decimal_input(amount, 'payment amount', precision)
    expected = _decimal_input(expected_outstanding, 'reviewed balance', precision)
    number = str(reference_no or '').strip()
    if len(number) > 140:
        frappe.throw('Enter a transaction reference of up to 140 characters.')
    reference = ''
    if reference_date:
        try:
            reference = str(date.fromisoformat(str(reference_date)))
        except ValueError:
            frappe.throw('Enter a valid transaction reference date.')
    balance = _balance(invoice, locked[0][0])

    # Exact retries after a lost response return the posted receipt.
    prior = frappe.db.sql(f'SELECT name FROM `tabPayment Entry` WHERE `{REQUEST_KEY}`=%s FOR UPDATE', (request_key,))
    if prior:
        existing = frappe.get_doc('Payment Entry', prior[0][0])
        refs = existing.references
        if (existing.docstatus == 1 and existing.company == invoice.company and existing.party == invoice.customer
                and _matching_references(refs, invoice.name)
                and sum(_balance(invoice, row.allocated_amount) for row in refs) == amount
                and existing.mode_of_payment == mode_of_payment and (existing.reference_no or '') == number
                and str(existing.reference_date or '') == reference):
            return {'payment_entry': existing.name, 'invoice': invoice.name, 'outstanding': str(balance), 'already_recorded': True}
        frappe.throw('This payment request has already been used. Reload the invoice and review its balance.')

    if balance != expected or _balance(invoice, invoice.outstanding_amount) != balance:
        frappe.throw('The outstanding balance changed. Reopen the payment form and review it again.')
    if not 0 < amount <= balance:
        frappe.throw('Payment must be greater than zero and within the outstanding balance.')
    mode = _accounts(invoice.company, currency).get(mode_of_payment)
    if not mode:
        frappe.throw('Choose a configured Cash or Bank Mode of Payment.')
    if mode['needs_reference'] and not (number and reference):
        frappe.throw('Bank payments require a transaction reference and date.')
    if bool(number) != bool(reference):
        frappe.throw('Enter both the transaction reference and its date.')
    if reference and reference > nowdate():
        frappe.throw('Transaction date cannot be in the future.')

    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

    account = mode['account']
    payment = get_payment_entry('Sales Invoice', invoice.name, bank_account=account, bank_amount=float(amount))
    refs = payment.references
    if (payment.company != invoice.company or payment.payment_type != 'Receive'
            or payment.party_type != 'Customer' or payment.party != invoice.customer
            or payment.paid_from != invoice.debit_to or payment.paid_to != account
            or not _matching_references(refs, invoice.name)):
        frappe.throw('ERPNext returned an unexpected payment allocation. Review the invoice in ERPNext.')
    payment.mode_of_payment = mode_of_payment
    payment.paid_amount = payment.received_amount = float(amount)
    _allocate(payment, invoice, amount)
    payment.reference_no = number or None
    payment.reference_date = reference or None
    payment.set(REQUEST_KEY, request_key)
    payment.insert()
    payment.submit()
    latest = frappe.db.sql('SELECT outstanding_amount FROM `tabSales Invoice` WHERE name=%s FOR UPDATE',
                           (invoice.name,))
    remaining = _balance(invoice, latest[0][0])
    if payment.docstatus != 1 or remaining != balance - amount:
        frappe.throw('ERPNext did not confirm the expected receipt and remaining balance.')
    return {'payment_entry': payment.name, 'invoice': invoice.name, 'outstanding': str(remaining), 'already_recorded': False}
