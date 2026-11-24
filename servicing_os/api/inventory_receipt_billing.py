"""Bill a submitted Purchase Receipt and settle its linked supplier invoices."""
import re
from datetime import date

import frappe
from frappe.utils import nowdate

from servicing_os.api.inventory_workspace import _company
from servicing_os.api.invoice_payment import REQUEST_KEY, _accounts, _allocate, _balance
from servicing_os.api.invoice_review import _decimal_input

RECEIPT = "Purchase Receipt"
INVOICE = "Purchase Invoice"
PAYMENT = "Payment Entry"


def _document(doctype, name, *, lock=False):
    company = _company()
    name = str(name or "").strip()
    if not name or len(name) > 140:
        frappe.throw(f"Select a saved {doctype}.")
    doc = frappe.get_doc(doctype, name, for_update=lock)
    if doc.company != company:
        frappe.throw(f"{doctype} is outside the active shop.", frappe.PermissionError)
    doc.check_permission("read")
    return doc


def _require(doctype, permission):
    if not frappe.has_permission(doctype, permission):
        frappe.throw(f"{doctype} {permission} permission is required.", frappe.PermissionError)


def _has_workflow(doctype):
    return bool(frappe.db.exists("Workflow", {"document_type": doctype, "is_active": 1}))


def _invoice_item_filters(receipt):
    return {"purchase_receipt": receipt.name, "parenttype": INVOICE, "parentfield": "items"}


def _invoice_names(receipt):
    # Also include invoices that were created before the receipt (PI -> PR).
    direct = frappe.get_all("Purchase Invoice Item", filters=_invoice_item_filters(receipt),
                            pluck="parent", distinct=True)
    reverse = [row.get("purchase_invoice") for row in receipt.get("items") or []]
    return sorted(set(direct + [name for name in reverse if name]))


def _linked_invoice(receipt, name, *, lock=False):
    invoice = _document(INVOICE, name, lock=lock)
    forward = any(row.get("purchase_receipt") == receipt.name for row in invoice.get("items") or [])
    reverse = any(row.get("purchase_invoice") == invoice.name for row in receipt.get("items") or [])
    if invoice.supplier != receipt.supplier or not (forward or reverse):
        frappe.throw("This invoice is not linked to the selected receipt.", frappe.PermissionError)
    return invoice


def _can_bill(receipt):
    return (int(receipt.docstatus) == 1 and not receipt.get("is_return")
            and receipt.get("status") != "Closed" and float(receipt.get("per_billed") or 0) < 100)


def _draft_invoicing_allowed(receipt, invoice):
    items = invoice.get("items") or []
    return (int(invoice.docstatus) == 0 and not invoice.get("is_return") and not invoice.get("update_stock")
            and not invoice.get("is_paid")
            and _can_bill(receipt) and bool(items)
            and all(row.get("purchase_receipt") == receipt.name and row.get("pr_detail") for row in items))


def _quick_payment_allowed():
    return all(frappe.has_permission(PAYMENT, action) for action in ("create", "submit")) and not _has_workflow(PAYMENT)


@frappe.whitelist(methods=["GET"])
def get_receipt_billing(receipt_name):
    receipt = _document(RECEIPT, receipt_name)
    can_read = bool(frappe.has_permission(INVOICE, "read"))
    can_bill = bool(frappe.has_permission(INVOICE, "create")) and _can_bill(receipt)
    linked = _invoice_names(receipt) if can_read else []
    invoices = frappe.get_list(INVOICE, filters={
        "company": receipt.company, "supplier": receipt.supplier, "name": ["in", linked], "docstatus": ["in", [0, 1]],
    }, fields=["name", "docstatus", "status", "bill_no", "posting_date", "due_date", "currency", "party_account_currency",
               "grand_total", "rounded_total", "outstanding_amount", "is_return", "on_hold", "release_date"],
       order_by="posting_date desc, name desc", limit_page_length=len(linked)) if linked else []
    can_pay = _quick_payment_allowed() if invoices else False
    today = nowdate()
    company_currency = frappe.get_cached_value("Company", receipt.company, "default_currency") if can_pay else None
    for row in invoices:
        held = row.on_hold and (not row.release_date or str(row.release_date) > today)
        row["can_pay"] = bool(can_pay and int(receipt.docstatus) == 1 and not receipt.get("is_return")
                              and int(row.docstatus) == 1 and not row.is_return and not held
                              and company_currency == row.currency == row.party_account_currency
                              and float(row.outstanding_amount or 0) > 0)
    return {
        "name": receipt.name, "supplier": receipt.get("supplier_name") or receipt.supplier,
        "status": receipt.get("status"), "docstatus": int(receipt.docstatus), "is_return": bool(receipt.get("is_return")),
        "posting_date": str(receipt.get("posting_date") or ""), "today": today,
        "can_bill": can_bill and can_read, "can_read_invoices": can_read, "invoices": invoices,
    }


@frappe.whitelist(methods=["POST"])
def create_receipt_invoice(receipt_name, bill_no=None, bill_date=None):
    from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

    _require(INVOICE, "create")
    _require(INVOICE, "read")
    receipt = _document(RECEIPT, receipt_name, lock=True)
    if not _can_bill(receipt):
        frappe.throw("Choose an open, submitted receipt with an unbilled amount.")
    existing = frappe.db.get_value("Purchase Invoice Item", {**_invoice_item_filters(receipt), "docstatus": 0},
                                   "parent", for_update=True)
    if existing:
        draft = _linked_invoice(receipt, existing)
        return {"name": draft.name, "already_exists": True}
    number = str(bill_no or "").strip()
    if len(number) > 140:
        frappe.throw("Enter a supplier invoice number of up to 140 characters.")
    vendor_date = None
    if bill_date:
        try:
            vendor_date = str(date.fromisoformat(str(bill_date)))
        except ValueError:
            frappe.throw("Enter a valid supplier invoice date.")
        if vendor_date > nowdate():
            frappe.throw("The supplier invoice date cannot be in the future.")

    invoice = make_purchase_invoice(receipt.name)
    invoice.update_stock = 0
    if number:
        invoice.bill_no = number
    if vendor_date:
        invoice.bill_date = vendor_date
    if invoice.company != receipt.company or invoice.supplier != receipt.supplier or not _draft_invoicing_allowed(receipt, invoice):
        frappe.throw("ERPNext could not map the receipt to a draft invoice.")
    invoice.insert()
    if int(invoice.docstatus) != 0:
        frappe.throw("The Purchase Invoice did not save as a draft.")
    return {"name": invoice.name, "already_exists": False}


@frappe.whitelist(methods=["GET"])
def get_linked_invoice(receipt_name, invoice_name):
    receipt = _document(RECEIPT, receipt_name)
    invoice = _linked_invoice(receipt, invoice_name)
    can_submit = (_draft_invoicing_allowed(receipt, invoice) and not _has_workflow(INVOICE)
                  and frappe.has_permission(INVOICE, "submit", doc=invoice))
    return {
        "name": invoice.name, "supplier": invoice.get("supplier_name") or invoice.supplier,
        "currency": invoice.currency, "status": invoice.get("status"), "docstatus": int(invoice.docstatus),
        "modified": str(invoice.modified), "can_submit": bool(can_submit),
        "bill_no": invoice.get("bill_no"), "bill_date": str(invoice.get("bill_date") or ""),
        "due_date": str(invoice.get("due_date") or ""), "posting_date": str(invoice.get("posting_date") or ""),
        "total": invoice.get("rounded_total") or invoice.get("grand_total"),
        "outstanding": invoice.get("outstanding_amount"), "outstanding_currency": invoice.get("party_account_currency"),
        "items": [{"name": row.get("name"), "item": row.get("item_name") or row.get("item_code"), "qty": row.get("qty"),
                   "uom": row.get("uom"), "rate": row.get("rate"), "amount": row.get("amount")}
                  for row in invoice.get("items") or []],
    }


@frappe.whitelist(methods=["POST"])
def submit_receipt_invoice(receipt_name, invoice_name, expected_modified):
    _require(INVOICE, "submit")
    receipt = _document(RECEIPT, receipt_name, lock=True)
    invoice = _linked_invoice(receipt, invoice_name, lock=True)
    invoice.check_permission("submit")
    if int(invoice.docstatus) == 1:
        return {"name": invoice.name, "already_submitted": True}
    if str(invoice.modified) != str(expected_modified or ""):
        frappe.throw("The draft changed after review. Reopen it to review the latest figures.")
    if not _draft_invoicing_allowed(receipt, invoice) or _has_workflow(INVOICE):
        frappe.throw("Review and submit this Purchase Invoice in ERPNext.")
    invoice.submit()
    if int(invoice.docstatus) != 1:
        frappe.throw("The Purchase Invoice did not reach Submitted status.")
    return {"name": invoice.name, "already_submitted": False}


def _payable_invoice(receipt_name, invoice_name, *, lock=False):
    if not _quick_payment_allowed():
        frappe.throw("Record this supplier payment in ERPNext with the required accounting permissions.")
    receipt = _document(RECEIPT, receipt_name)
    invoice = _linked_invoice(receipt, invoice_name, lock=lock)
    if (int(receipt.docstatus) != 1 or receipt.get("is_return") or int(invoice.docstatus) != 1
            or invoice.get("is_return") or invoice.invoice_is_blocked()):
        frappe.throw("Payment requires a submitted, payable invoice. Review the invoice for holds or returns.")
    currency = frappe.get_cached_value("Company", invoice.company, "default_currency")
    payable_currency = frappe.db.get_value("Account", invoice.credit_to, "account_currency")
    if not currency or invoice.currency != currency or payable_currency != currency:
        frappe.throw("Record foreign-currency supplier payments in ERPNext.")
    if not frappe.db.has_column(PAYMENT, REQUEST_KEY):
        frappe.throw("Payment tracking is unavailable. Run bench migrate.")
    return invoice, currency


@frappe.whitelist(methods=["GET"])
def get_supplier_payment_context(receipt_name, invoice_name):
    invoice, currency = _payable_invoice(receipt_name, invoice_name)
    outstanding = _balance(invoice, invoice.outstanding_amount)
    if outstanding <= 0:
        frappe.throw("This invoice has no outstanding balance.")
    methods = _accounts(invoice.company, currency)
    if not methods:
        frappe.throw("Configure an enabled Cash or Bank Mode of Payment with a company account in ERPNext.")
    return {"outstanding": str(outstanding), "currency": currency, "precision": invoice.precision("outstanding_amount"),
            "posting_date": nowdate(), "methods": [{"name": name, **mode} for name, mode in methods.items()]}


def _matches_invoice(payment, invoice):
    return (payment.company == invoice.company and payment.payment_type == "Pay" and payment.party_type == "Supplier"
            and payment.party == invoice.supplier and payment.paid_to == invoice.credit_to and bool(payment.references)
            and all(row.reference_doctype == INVOICE and row.reference_name == invoice.name for row in payment.references))


@frappe.whitelist(methods=["POST"])
def record_supplier_payment(receipt_name, invoice_name, amount, mode_of_payment, expected_outstanding, request_key,
                            reference_no=None, reference_date=None):
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

    if not re.fullmatch("[0-9a-f]{32}", str(request_key or "")):
        frappe.throw("Reopen the payment form to start a new payment.")
    invoice, currency = _payable_invoice(receipt_name, invoice_name, lock=True)
    precision = invoice.precision("outstanding_amount")
    amount = _decimal_input(amount, "payment amount", precision)
    expected = _decimal_input(expected_outstanding, "reviewed balance", precision)
    number = str(reference_no or "").strip()
    reference = str(reference_date or "")
    if len(number) > 140 or bool(number) != bool(reference):
        frappe.throw("Enter both a transaction reference of up to 140 characters and its date.")
    if reference:
        try:
            reference = str(date.fromisoformat(reference))
        except ValueError:
            frappe.throw("Enter a valid transaction reference date.")
        if reference > nowdate():
            frappe.throw("Transaction date cannot be in the future.")

    balance = _balance(invoice, invoice.outstanding_amount)
    prior = frappe.db.get_value(PAYMENT, {REQUEST_KEY: request_key}, "name", for_update=True)
    if prior:
        existing = frappe.get_doc(PAYMENT, prior)
        if (int(existing.docstatus) == 1 and _matches_invoice(existing, invoice)
                and sum(_balance(invoice, row.allocated_amount) for row in existing.references) == amount
                and existing.mode_of_payment == mode_of_payment and (existing.reference_no or "") == number
                and str(existing.reference_date or "") == reference):
            return {"payment_entry": existing.name, "outstanding": str(balance), "already_recorded": True}
        frappe.throw("This payment request was already used. Reopen the invoice and review its balance.")
    if expected != balance:
        frappe.throw("The outstanding balance changed. Reopen the payment form to review it.")
    if not 0 < amount <= balance:
        frappe.throw("Payment must be positive and within the outstanding balance.")
    mode = _accounts(invoice.company, currency).get(mode_of_payment)
    if not mode or (mode["needs_reference"] and not reference):
        frappe.throw("Select a configured payment method. Bank payments require a reference and date.")

    account = mode["account"]
    payment = get_payment_entry(INVOICE, invoice.name, bank_account=account)
    if (not _matches_invoice(payment, invoice) or payment.paid_from != account
            or payment.get("deductions") or payment.get("taxes") or _balance(invoice, payment.paid_amount) != balance
            or any(row.get("payment_request") for row in payment.references)):
        frappe.throw("Review deductions, payment discounts or payment requests in ERPNext before recording this payment.")
    _allocate(payment, invoice, amount)
    payment.mode_of_payment = mode_of_payment
    payment.paid_amount = payment.received_amount = float(amount)
    payment.reference_no = number or None
    payment.reference_date = reference or None
    payment.set(REQUEST_KEY, request_key)
    payment.insert()
    payment.submit()
    remaining = _balance(invoice, frappe.db.get_value(INVOICE, invoice.name, "outstanding_amount", for_update=True))
    if int(payment.docstatus) != 1 or remaining != balance - amount:
        frappe.throw("ERPNext did not confirm the payment and the expected remaining balance.")
    return {"payment_entry": payment.name, "outstanding": str(remaining), "already_recorded": False}
