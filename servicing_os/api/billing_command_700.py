"""SERVICING OS 7.00 — read-only, permission-aware billing intelligence.

Financial transactions remain exclusively in ERPNext's existing invoicing,
payment and delivery workflows. This module never posts or changes documents.
"""
from collections import defaultdict
from datetime import date, timedelta

import frappe
from frappe.utils import flt, getdate, nowdate

MAX_DOCS = 5000
CATALOG = [
    ("Sales & revenue", ["Sales Register", "Item-wise Sales Register", "Sales Analytics", "Gross Profit", "Sales Invoice Trends", "Sales Taxes and Charges"]),
    ("Receivables & customer credit", ["Accounts Receivable", "Accounts Receivable Summary", "Payment Ledger", "Customer Credit Balance", "Payment Period Based On Invoice Date"]),
    ("Cash, banks & settlements", ["Cash Flow", "Bank Reconciliation Statement", "Bank Clearance Summary", "Bank Account Balance", "POS Closing Entry"]),
    ("Core financial statements", ["Profit and Loss Statement", "Balance Sheet", "Trial Balance", "General Ledger", "Financial Statements", "Consolidated Financial Statement"]),
    ("Purchases, supplier dues & tax", ["Purchase Register", "Purchase Analytics", "Accounts Payable", "Accounts Payable Summary", "Purchase Taxes and Charges", "Tax Withholding Details"]),
    ("Inventory, margin & controls", ["Stock Ledger", "Stock Balance", "Stock Ageing", "Stock and Account Value Comparison", "Budget Variance Report", "Profitability Analysis"]),
    ("Expenses, cost centers & assets", ["Expense Claim Summary", "Cost Center-wise Profit and Loss", "Asset Depreciation Ledger", "Fixed Asset Register", "Monthly Distribution", "Purchase Invoice Trends"]),
]


def _company():
    # Never silently aggregate different companies. Read the active shop config.
    company = ""
    if frappe.has_permission("Servicing Shop", "read"):
        shops = frappe.get_list(
            "Servicing Shop", filters={"is_active": 1},
            fields=["company"], limit_page_length=1
        )
        if shops:
            company = shops[0].get("company") or ""
    company = company or frappe.defaults.get_user_default("Company")
    if not company:
        permitted = frappe.get_list("Company", fields=["name"], limit_page_length=2)
        if len(permitted) == 1:
            company = permitted[0].name
    if not company:
        frappe.throw("Select your company in User Defaults or configure the active Servicing Shop.")
    if not frappe.db.exists("Company", company):
        frappe.throw("Configured company is not present in ERPNext.")
    return company


def _dates(start_date=None, end_date=None):
    today = getdate(nowdate())
    end = getdate(end_date) if end_date else today
    start = getdate(start_date) if start_date else end - timedelta(days=29)
    if start > end:
        frappe.throw("From Date must not be after To Date.")
    if (end - start).days > 730:
        frappe.throw("Select a period of 731 days or less.")
    return start, end


def _need(doctype):
    if not frappe.has_permission(doctype, "read"):
        frappe.throw("Read permission is required for " + doctype, frappe.PermissionError)


def _list(doctype, fields, filters, limit=MAX_DOCS):
    # frappe.get_list enforces standard document permissions / user permissions.
    rows = frappe.get_list(doctype, fields=fields, filters=filters,
                           order_by="modified desc", limit_page_length=limit + 1)
    if len(rows) > limit:
        frappe.throw("More than %s %s records match the period. Select a shorter date range to avoid incomplete totals." % (limit, doctype))
    return rows


def _invoices(company, start, end):
    meta = frappe.get_meta("Sales Invoice")
    fields = ["name", "posting_date", "due_date", "customer", "customer_name", "status",
              "base_net_total", "base_grand_total", "base_total_taxes_and_charges",
              "outstanding_amount", "is_return", "currency"]
    if meta.has_field("custom_service_job"):
        fields.append("custom_service_job")
    filters = {"company": company, "docstatus": 1,
               "posting_date": ["between", [str(start), str(end)]]}
    return _list("Sales Invoice", fields, filters)


def _payments(company, start, end):
    if not frappe.has_permission("Payment Entry", "read"):
        return None
    return _list("Payment Entry", ["name", "posting_date", "party", "party_name", "payment_type",
                                    "base_received_amount", "base_paid_amount", "mode_of_payment"],
                 {"company": company, "docstatus": 1,
                  "posting_date": ["between", [str(start), str(end)]]})


def _delivery(company):
    if not frappe.has_permission("Service Job", "read"):
        return {"visible": False, "ready": None, "delivered": None, "jobs": []}
    meta = frappe.get_meta("Service Job")
    fields = ["name", "status", "customer_name", "device_type", "device_model", "serial_number", "modified"]
    fields = [f for f in fields if f == 'name' or meta.has_field(f)]
    # Scope service jobs by the active company's readable Servicing Shops, not
    # all shops from every company. If that cannot be established, omit pulse.
    filters = {}
    if meta.has_field("shop"):
        if not frappe.has_permission("Servicing Shop", "read"):
            return {"visible": False, "ready": None, "delivered": None, "jobs": [], "reason": "shop scope unavailable"}
        shops = frappe.get_list("Servicing Shop", fields=["name"], filters={"company": company}, limit_page_length=500)
        if not shops:
            return {"visible": False, "ready": None, "delivered": None, "jobs": [], "reason": "no accessible shops"}
        filters = {"shop": ["in", [s.name for s in shops]]}
    elif meta.has_field("company"):
        filters = {"company": company}
    else:
        return {"visible": False, "ready": None, "delivered": None, "jobs": [], "reason": "company association unavailable"}
    jobs = frappe.get_list("Service Job", fields=fields, filters=filters, order_by="modified desc", limit_page_length=200)
    ready = [r for r in jobs if r.get("status") in ("Ready to Deliver", "Completed")]
    delivered = [r for r in jobs if r.get("status") == "Delivered"]
    return {"visible": True, "ready": len(ready), "delivered": len(delivered),
            "jobs": ready[:30], "scanned": len(jobs), "is_sample": True}


@frappe.whitelist()
def get_overview(start_date=None, end_date=None):
    _need("Sales Invoice")
    company = _company()
    start, end = _dates(start_date, end_date)
    invoices = _invoices(company, start, end)
    payments = _payments(company, start, end)
    daily = defaultdict(lambda: {"net": 0.0, "gross": 0.0, "count": 0})
    taxes, net, gross, outstanding, returns, overdue, count = (0.0,) * 7
    today = getdate(nowdate())
    for r in invoices:
        signed_net = flt(r.base_net_total)
        signed_gross = flt(r.base_grand_total)
        tax = flt(r.base_total_taxes_and_charges)
        # Submitted return invoices are negative in ERPNext; don't subtract again.
        net += signed_net
        gross += signed_gross
        taxes += tax
        outstanding += flt(r.outstanding_amount)
        if flt(r.is_return):
            returns += abs(signed_gross)
        if r.due_date and getdate(r.due_date) < today and flt(r.outstanding_amount) > 0:
            overdue += flt(r.outstanding_amount)
        if not flt(r.is_return):
            count += 1
        point = daily[str(r.posting_date)]
        point["net"] += signed_net
        point["gross"] += signed_gross
        point["count"] += 1
    collections = None
    payment_count = None
    if payments is not None:
        receipts = [p for p in payments if p.payment_type == "Receive"]
        collections = sum(flt(p.base_received_amount) for p in receipts)
        payment_count = len(receipts)
    # Calendar-aligned chart: empty days are genuine zeros, no fabricated sales.
    series = []
    cursor = start
    while cursor <= end:
        v = daily[str(cursor)]
        series.append({"date": str(cursor), "net": round(v["net"], 2),
                       "gross": round(v["gross"], 2), "invoice_count": v["count"]})
        cursor += timedelta(days=1)
    return {"company": company, "currency": frappe.get_cached_value("Company", company, "default_currency") or "BDT",
            "start_date": str(start), "end_date": str(end), "invoice_count": int(count),
            "net_revenue": round(net, 2), "gross_invoiced": round(gross, 2),
            "taxes": round(taxes, 2), "returns_gross": round(returns, 2),
            "invoice_outstanding_current": round(outstanding, 2),
            "invoice_overdue_current": round(overdue, 2),
            "received_payments": None if collections is None else round(collections, 2),
            "payment_count": payment_count, "daily": series,
            "delivery": _delivery(company),
            "notes": [
                "Revenue uses submitted Sales Invoices dated in the selected period; returns preserve their accounting sign.",
                "Outstanding and overdue are current unpaid amounts on only those selected invoices, not full-company AR aging.",
                "Received payments are submitted Receive-type Payment Entries in the period; advances may be included, so do not add these to invoice revenue.",
                "Delivery counts are from a sample of 200 recent authorized jobs and are not all-time totals.",
                "Use standard ERPNext GL, P&L, cash flow and AR/AP reports for authoritative accounting statements.",
            ]}


@frappe.whitelist()
def get_register(kind="invoices", start_date=None, end_date=None, q="", page=1):
    company = _company()
    start, end = _dates(start_date, end_date)
    page = max(1, min(int(page or 1), 200))
    q = str(q or "").strip()[:90].lower()
    if kind in ("invoices", "dues"):
        _need("Sales Invoice")
        docs = _invoices(company, start, end)
        if kind == "dues":
            docs = [r for r in docs if flt(r.outstanding_amount) > 0]
        if q:
            docs = [r for r in docs if q in (" ".join(str(r.get(k) or "") for k in
                       ("name", "customer", "customer_name", "status", "custom_service_job"))).lower()]
        docs.sort(key=lambda r: (str(r.posting_date), r.name), reverse=True)
        result = [{"name": r.name, "date": str(r.posting_date), "party": r.customer_name or r.customer,
                   "type": "Return" if r.is_return else "Service" if r.get("custom_service_job") else "Sale",
                   "status": r.status, "net": flt(r.base_net_total), "gross": flt(r.base_grand_total),
                   "outstanding": flt(r.outstanding_amount), "due_date": str(r.due_date or ""),
                   "service_job": r.get("custom_service_job") or ""} for r in docs]
    elif kind == "payments":
        _need("Payment Entry")
        docs = _payments(company, start, end) or []
        if q:
            docs = [r for r in docs if q in (" ".join(str(r.get(k) or "") for k in
                       ("name", "party", "party_name", "payment_type", "mode_of_payment"))).lower()]
        result = [{"name": r.name, "date": str(r.posting_date), "party": r.party_name or r.party,
                   "type": r.payment_type, "mode": r.mode_of_payment,
                   "received": flt(r.base_received_amount), "paid": flt(r.base_paid_amount)} for r in docs]
    else:
        frappe.throw("Unsupported register type")
    size = 50
    offset = (page - 1) * size
    return {"company": company, "kind": kind, "total": len(result), "page": page,
            "page_size": size, "has_next": offset + size < len(result),
            "rows": result[offset:offset + size]}


@frappe.whitelist()
def get_report_catalog():
    # Metadata only, no report execution or bypass of report permissions.
    groups = []
    for category, names in CATALOG:
        groups.append({"category": category, "reports": [
            {"name": n, "available": bool(frappe.db.exists("Report", n))} for n in names
        ]})
    # Include site-specific accounting/financial reports when the current user
    # can list Report records; respect Report DocType read permissions.
    known = {name for _, names in CATALOG for name in names}
    doctypes = ["Sales Invoice", "Purchase Invoice", "Payment Entry", "GL Entry",
                "Journal Entry", "Account", "Bank Transaction", "Stock Ledger Entry",
                "Customer", "Supplier", "Company", "POS Invoice", "Budget", "Expense Claim",
                "Employee Advance", "Cost Center", "Asset", "Delivery Note", "Sales Order",
                "Purchase Order", "Purchase Receipt", "POS Closing Entry"]
    if frappe.has_permission("Report", "read"):
        installed = frappe.get_list("Report", fields=["name", "ref_doctype"],
                    filters={"ref_doctype": ["in", doctypes]},
                    order_by="name asc", limit_page_length=1000)
        extra = sorted({r.name for r in installed if r.name not in known})
        if extra:
            groups.append({"category": "Other installed finance & accounting reports",
                           "reports": [{"name": name, "available": True} for name in extra]})
    return {"groups": groups, "company": _company(),
            "note": "Reports open using ERPNext's native role checks, report filters and accounting logic."}
