"""Cash collection using native ERPNext Payment Entry.

Step 6.17A. Browsing endpoints are read-only; create_cash_payment_draft
creates only a DRAFT and never posts the General Ledger. Never use this
API for a non-servicing invoice.
"""
import math
import frappe
from decimal import Decimal, InvalidOperation
from frappe.utils import flt
from servicing_os.api.site_company_706 import cash_account, current_company, current_currency

INVOICE_JOB_FIELD = "custom_service_job"


def _cash_configuration():
    name = cash_account()
    account = frappe.db.get_value(
        "Account", name,
        ["company", "account_type", "is_group", "disabled"], as_dict=True,
    ) if name else None
    if not account or account.company != current_company() or account.account_type != "Cash" \
            or account.is_group or account.disabled:
        frappe.throw("Configure an active company Cash ledger on the Cash Mode of Payment.")
    mode = frappe.db.get_value("Mode of Payment", "Cash", ["enabled", "type"], as_dict=True)
    if not mode or not mode.enabled or mode.type != "Cash":
        frappe.throw("An enabled Cash Mode of Payment is required.")
    return name


def _invoice(invoice_name, *, outstanding_required=False):
    if not frappe.has_permission("Sales Invoice", "read"):
        frappe.throw("Sales Invoice read permission required.", frappe.PermissionError)
    if not frappe.get_meta("Sales Invoice").has_field(INVOICE_JOB_FIELD):
        frappe.throw("Step 6.16A Service Job link field is missing on Sales Invoice.")
    doc = frappe.get_doc("Sales Invoice", invoice_name)
    doc.check_permission("read")
    if doc.company != current_company() or not doc.get(INVOICE_JOB_FIELD):
        frappe.throw("Select an service-job Sales Invoice.")
    if doc.docstatus != 1 or doc.is_return:
        frappe.throw("Cash payment requires a submitted non-return Sales Invoice.")
    if doc.currency != current_currency():
        frappe.throw("This first cash workflow handles BDT invoices only.")
    if outstanding_required and flt(doc.outstanding_amount) <= 0:
        frappe.throw("Invoice has no outstanding balance.")
    return doc


def _money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        frappe.throw("Enter a valid payment amount.")
    if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal("0.01")):
        frappe.throw("Payment must be positive, finite, and have at most 2 decimal places.")
    return amount


@frappe.whitelist()
def get_cash_collection_overview(limit=100):
    """Read-only list of submitted AMCL service invoices and their dues."""
    if not frappe.has_permission("Sales Invoice", "read"):
        frappe.throw("Sales Invoice read permission required.", frappe.PermissionError)
    if not frappe.get_meta("Sales Invoice").has_field(INVOICE_JOB_FIELD):
        frappe.throw("Service Job invoice link field missing. Run Step 6.16A first.")
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(limit, 200))
    invoices = frappe.get_list(
        "Sales Invoice",
        filters={"company": current_company(), "docstatus": 1, "is_return": 0,
                 INVOICE_JOB_FIELD: ["is", "set"]},
        fields=["name", "customer", "posting_date", "currency", "grand_total",
                "outstanding_amount", "status", INVOICE_JOB_FIELD],
        order_by="posting_date desc, creation desc", limit_page_length=limit,
    )
    return {
        "company": current_company(), "currency": current_currency(), "cash_account": cash_account(),
        "invoices": invoices, "count": len(invoices),
        "can_create_payment": bool(frappe.has_permission("Payment Entry", "create")),
        "note": "Submitted invoices only. Outstanding values come from ERPNext, not repair estimates.",
    }


@frappe.whitelist()
def preview_cash_payment(invoice_name):
    """Read-only payment readiness; no Payment Entry created."""
    inv = _invoice(invoice_name, outstanding_required=True)
    account = _cash_configuration()
    return {
        "invoice": inv.name, "service_job": inv.get(INVOICE_JOB_FIELD),
        "customer": inv.customer, "currency": inv.currency,
        "invoice_total": inv.grand_total,
        "outstanding_amount": inv.outstanding_amount,
        "mode_of_payment": "Cash", "paid_to": account,
        "can_create_payment": bool(frappe.has_permission("Payment Entry", "create")),
        "draft_only": True,
    }


@frappe.whitelist(methods=["POST"])
def create_cash_payment_draft(invoice_name, amount):
    """Make a DRAFT Payment Entry via ERPNext's native invoice mapping.

    This is an explicit, permission-checked action. Does NOT submit or post
    cash/general-ledger changes. Submission must happen in ERPNext Desk.
    """
    if not frappe.has_permission("Payment Entry", "create"):
        frappe.throw("Payment Entry create permission required.", frappe.PermissionError)
    inv = _invoice(invoice_name, outstanding_required=True)
    account = _cash_configuration()
    amount = _money(amount)
    outstanding = Decimal(str(inv.outstanding_amount)).quantize(Decimal("0.01"))
    if amount > outstanding:
        frappe.throw("Payment cannot exceed the current invoice outstanding amount.")

    # Avoid accidental parallel drafts from this workflow.
    prior = frappe.db.sql(
        """select pe.name from `tabPayment Entry` pe
           inner join `tabPayment Entry Reference` r on r.parent = pe.name
           where pe.docstatus = 0 and r.parenttype = 'Payment Entry'
             and r.reference_doctype = 'Sales Invoice'
             and r.reference_name = %s limit 1""", (inv.name,), as_dict=True,
    )
    if prior:
        frappe.throw("An existing draft Payment Entry already references this invoice: " + prior[0].name)

    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    payment = get_payment_entry(
        "Sales Invoice", inv.name, bank_account=account, bank_amount=float(amount)
    )
    # Preserve ERPNext's mapped customer/receivables and FX details; restrict
    # this first version to same-currency cash transactions.
    if payment.payment_type != "Receive" or payment.party_type != "Customer" \
            or payment.party != inv.customer or payment.company != current_company():
        frappe.throw("Unexpected native Payment Entry mapping; no document saved.")

    payment.mode_of_payment = "Cash"
    payment.paid_to = account
    payment.paid_amount = float(amount)
    payment.received_amount = float(amount)

    matching = [r for r in payment.references
                if r.reference_doctype == "Sales Invoice" and r.reference_name == inv.name]
    if len(matching) != 1 or len(payment.references) != 1:
        frappe.throw("Expected exactly one invoice payment allocation.")
    matching[0].allocated_amount = float(amount)

    payment.insert()  # Standard ERPNext validations and permissions.
    if payment.docstatus != 0 or payment.payment_type != "Receive" \
            or payment.paid_to != account:
        frappe.throw("Payment safety assertion failed; transaction rolled back.")

    return {
        "success": True, "payment_entry": payment.name, "docstatus": 0,
        "sales_invoice": inv.name, "service_job": inv.get(INVOICE_JOB_FIELD),
        "amount": float(amount), "currency": current_currency(),
        "submitted": False, "ledger_posted": False,
        "message": "Draft only. Review and submit in ERPNext Desk after actually collecting cash.",
    }
