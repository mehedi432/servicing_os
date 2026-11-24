"""Permission-aware ERPNext transaction history for Customer and Supplier 360."""
from collections import defaultdict
from datetime import date
from decimal import Decimal

import frappe
from frappe.utils import nowdate

from servicing_os.api.site_company_706 import current_currency, site_shop_context


INVOICE_FIELDS = ("posting_date", "due_date", "currency", "status", "grand_total",
                  "base_grand_total", "base_net_total", "outstanding_amount",
                  "party_account_currency", "is_return")
PAYMENT_FIELDS = ("posting_date", "payment_type", "mode_of_payment", "reference_no",
                  "base_paid_amount", "base_received_amount")
ORDER_FIELDS = ("transaction_date", "status", "currency", "grand_total")
PURCHASE_ORDER_FIELDS = (*ORDER_FIELDS, "schedule_date", "per_received", "per_billed")
RECEIPT_PENDING = ("To Receive and Bill", "To Receive")
BILLING_PENDING = ("To Receive and Bill", "To Bill")
OPEN_PURCHASE_STATES = (*RECEIPT_PENDING, "To Bill", "On Hold")
HISTORY = {
    "Customer": {
        "invoices": ("Sales Invoice", "customer", "posting_date", (*INVOICE_FIELDS, "debit_to")),
        "open_invoices": ("Sales Invoice", "customer", "posting_date", (*INVOICE_FIELDS, "debit_to")),
        "orders": ("Sales Order", "customer", "transaction_date", ORDER_FIELDS),
        "payments": ("Payment Entry", "party", "posting_date", PAYMENT_FIELDS),
        "repairs": ("Service Job", "customer", "received_date",
                    ("received_date", "status", "device_type", "brand", "device_model")),
    },
    "Supplier": {
        "invoices": ("Purchase Invoice", "supplier", "posting_date", (*INVOICE_FIELDS, "credit_to", "bill_no")),
        "orders": ("Purchase Order", "supplier", "transaction_date", PURCHASE_ORDER_FIELDS),
        "payments": ("Payment Entry", "party", "posting_date", PAYMENT_FIELDS),
    },
}


def _query(party_type, party, section, scope):
    doctype, party_field, date_field, fields = HISTORY[party_type][section]
    filters = {party_field: party}
    if section == "repairs":
        filters["shop"] = scope["shop"]
    else:
        filters["company"] = scope["company"]
        filters["docstatus"] = ["in", [0, 1]]
    if section == "payments":
        filters.update(party_type=party_type, docstatus=1, payment_type=["in", ["Receive", "Pay"]])
    elif section == "open_invoices":
        filters.update(docstatus=1, outstanding_amount=[">", 0])

    meta = frappe.get_meta(doctype)
    return dict(doctype=doctype, filters=filters, order_by=f"{date_field} desc, creation desc, name desc",
                fields=["name", "docstatus", "creation", *(field for field in fields if meta.has_field(field))])


def _submitted_rows(query):
    filters = {**query["filters"], "docstatus": 1}
    request = {**query, "filters": filters}
    size = 250
    start = 0
    while True:
        rows = frappe.get_list(**request, limit_start=start, limit_page_length=size)
        yield from rows
        if len(rows) < size:
            return
        start += size


def _money(value):
    return Decimal(str(value or 0))


def _invoice_due_currency(row, currency):
    account = row.get("debit_to") or row.get("credit_to")
    account_currency = row.get("party_account_currency")
    if not account_currency and account:
        account_currency = frappe.get_cached_value("Account", account, "account_currency")
    return account_currency or row.get("currency") or currency


def open_supplier_order_counts(suppliers):
    """Count visible open orders with one grouped query for the directory page."""
    if not suppliers or not frappe.has_permission("Purchase Order", ptype="read"):
        return None
    rows = frappe.get_list(
        "Purchase Order",
        filters={"company": site_shop_context()["company"], "supplier": ["in", suppliers],
                 "docstatus": 1, "status": ["in", OPEN_PURCHASE_STATES]},
        fields=["supplier", "count(name) as order_count"], group_by="supplier",
        order_by="supplier asc", limit_page_length=len(suppliers),
    )
    return {row["supplier"]: int(row["order_count"]) for row in rows}


def _supplier_orders(party, scope):
    scope_filters = {"supplier": party, "company": scope["company"], "docstatus": 1}
    summary = frappe.get_list("Purchase Order", filters=scope_filters,
                              fields=["status", "count(name) as order_count", "sum(base_grand_total) as ordered_value"],
                              group_by="status", order_by="status asc", limit_page_length=0)
    counts = {row["status"]: int(row["order_count"]) for row in summary}
    open_count = sum(counts.get(status, 0) for status in OPEN_PURCHASE_STATES)
    meta = frappe.get_meta("Purchase Order")
    has_schedule = meta.has_field("schedule_date")
    today = nowdate()
    upcoming = []
    overdue = None
    if open_count:
        upcoming = frappe.get_list(
            "Purchase Order", filters={**scope_filters, "status": ["in", OPEN_PURCHASE_STATES]},
            fields=["name", *(field for field in PURCHASE_ORDER_FIELDS if meta.has_field(field))],
            order_by="schedule_date asc, name asc" if has_schedule else "transaction_date desc, name desc",
            limit_page_length=5,
        )
        for order in upcoming:
            date_required = order.get("schedule_date")
            order["receipt_overdue"] = bool(date_required and str(date_required) < today and order["status"] in RECEIPT_PENDING)
    if has_schedule:
        submitted_filters = [[field, "=", value] for field, value in scope_filters.items()]
        aged = frappe.get_list(
            "Purchase Order",
            filters=[*submitted_filters,
                     ["status", "in", RECEIPT_PENDING], ["schedule_date", "is", "set"], ["schedule_date", "<", today]],
            fields=["count(name) as order_count"], limit_page_length=1,
        )
        overdue = int(aged[0]["order_count"]) if aged else 0
    return {
        "submitted": sum(counts.values()),
        "open": open_count,
        "receiving": sum(counts.get(status, 0) for status in RECEIPT_PENDING),
        "billing": sum(counts.get(status, 0) for status in BILLING_PENDING),
        "on_hold": counts.get("On Hold", 0),
        "overdue": overdue,
        "ordered_value": float(sum(_money(row.get("ordered_value")) for row in summary)),
        "orders": upcoming,
    }


def profile(party_type, party):
    scope = site_shop_context()
    currency = current_currency(scope["company"])
    sections = [section for section, (doctype, *_) in HISTORY[party_type].items()
                if frappe.has_permission(doctype, ptype="read")]
    if party_type == "Customer" and frappe.has_permission("GL Entry", ptype="read"):
        sections.insert(0, "ledger")
    invoices = None
    payments = None

    if "invoices" in sections:
        net = billed = Decimal(0)
        due = defaultdict(Decimal)
        count = 0
        for row in _submitted_rows(_query(party_type, party, "invoices", scope)):
            net += _money(row.get("base_net_total"))
            billed += _money(row.get("base_grand_total"))
            due[_invoice_due_currency(row, currency)] += _money(row.get("outstanding_amount"))
            count += 1
        invoices = {
            "net": float(net), "billed": float(billed), "count": count,
            "due": {key: float(amount) for key, amount in due.items() if key and amount}
            or ({currency: 0} if currency else {}),
        }

    if "payments" in sections:
        cash = Decimal(0)
        count = 0
        first = None
        direction = "Receive" if party_type == "Customer" else "Pay"
        for row in _submitted_rows(_query(party_type, party, "payments", scope)):
            if first is None:
                first = {"posting_date": row.get("posting_date"), "creation": row.get("creation")}
            payment_type = row.get("payment_type")
            amount = _money(row.get("base_received_amount" if payment_type == "Receive" else "base_paid_amount"))
            cash += amount if payment_type == direction else -amount
            count += 1
        payments = {"net": float(cash), "count": count, "latest": first}

    order_summary = _supplier_orders(party, scope) if party_type == "Supplier" and "orders" in sections else None
    return {"company": scope["company"], "currency": currency, "sections": sections,
            "invoices": invoices, "payments": payments, "purchase_orders": order_summary}


def history(party_type, party, section, page):
    if section not in HISTORY[party_type]:
        frappe.throw("Choose an available transaction history.")
    doctype = HISTORY[party_type][section][0]
    if not frappe.has_permission(doctype, ptype="read"):
        frappe.throw(f"You need read permission for {doctype}.", frappe.PermissionError)
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        frappe.throw("Enter a valid history page.")

    scope = site_shop_context()
    currency = current_currency(scope["company"])
    query = _query(party_type, party, section, scope)
    size = 20
    data = frappe.get_list(**query, limit_start=(page - 1) * size, limit_page_length=size + 1)
    rows = []
    for entry in data[:size]:
        row = dict(entry)
        if section in ("invoices", "open_invoices"):
            row["due_currency"] = _invoice_due_currency(row, currency)
        elif section == "payments":
            payment_type = row.get("payment_type")
            row["amount"] = row.get("base_received_amount" if payment_type == "Receive" else "base_paid_amount")
            row["currency"] = currency
        rows.append(row)
    return {"rows": rows, "page": page, "has_next": len(data) > size}


def _ledger_totals(filters):
    result = frappe.get_list(
        "GL Entry", filters=filters, fields=["sum(debit) as total_debit", "sum(credit) as total_credit"],
        group_by="company", order_by="company asc", limit_page_length=1,
    )
    row = result[0] if result else {}
    return _money(row.get("total_debit")), _money(row.get("total_credit"))


def _ledger_carry(filters, first):
    posting = ["posting_date", "=", first["posting_date"]]
    created = ["creation", "=", first["creation"]]
    before = (
        [["posting_date", "<", first["posting_date"]]],
        [posting, ["creation", "<", first["creation"]]],
        [posting, created, ["name", "<", first["name"]]],
    )
    balance = Decimal(0)
    for earlier in before:
        debit, credit = _ledger_totals([*filters, *earlier])
        balance += debit - credit
    return balance


def customer_ledger(customer, from_date=None, to_date=None, page=1):
    if not frappe.has_permission("GL Entry", ptype="read"):
        frappe.throw("You need read permission for GL Entry.", frappe.PermissionError)
    try:
        start = date.fromisoformat(str(from_date)) if from_date else None
        end = date.fromisoformat(str(to_date)) if to_date else None
    except ValueError:
        frappe.throw("Enter valid ledger dates.")
    if start and end and start > end:
        frappe.throw("Ledger start date must be on or before the end date.")
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        frappe.throw("Enter a valid ledger page.")

    company = site_shop_context()["company"]
    base = [["company", "=", company], ["party_type", "=", "Customer"],
            ["party", "=", customer], ["is_cancelled", "=", 0]]
    filters = list(base)
    opening = Decimal(0)
    if start:
        filters.append(["posting_date", ">=", start.isoformat()])
        debit, credit = _ledger_totals([*base, ["posting_date", "<", start.isoformat()]])
        opening = debit - credit
    if end:
        filters.append(["posting_date", "<=", end.isoformat()])
    debit, credit = _ledger_totals(filters)
    size = 20
    data = frappe.get_list(
        "GL Entry", filters=filters,
        fields=["name", "creation", "posting_date", "account", "voucher_type", "voucher_no", "debit", "credit"],
        order_by="posting_date asc, creation asc, name asc", limit_start=(page - 1) * size,
        limit_page_length=size + 1,
    )
    balance = opening
    if page > 1 and data:
        balance += _ledger_carry(filters, data[0])
    rows = []
    for entry in data[:size]:
        balance += _money(entry.get("debit")) - _money(entry.get("credit"))
        rows.append({**entry, "balance": float(balance)})
    return {"rows": rows, "currency": current_currency(company), "page": page, "has_next": len(data) > size,
            "opening": float(opening), "debits": float(debit), "credits": float(credit),
            "closing": float(opening + debit - credit)}
