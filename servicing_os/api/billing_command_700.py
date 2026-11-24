"""Permission-aware billing reports and historical invoice labels."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import frappe
from frappe.utils import cint, flt, getdate, nowdate

from servicing_os.revenue_reporting import can_label, classification_fields, classifications
from servicing_os.revenue_streams import REPORT_STREAM_FIELD, STREAMS

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
        from servicing_os.api.site_company_706 import site_shop_context
        context = site_shop_context()
        shop = frappe.get_doc('Servicing Shop', context['shop'])
        shop.check_permission('read')
        company = shop.company
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
    fields.extend(classification_fields(meta))
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
def get_overview(start_date=None, end_date=None, include_delivery=True):
    _need("Sales Invoice")
    company = _company()
    start, end = _dates(start_date, end_date)
    invoices = _invoices(company, start, end)
    payments = _payments(company, start, end)
    daily = defaultdict(lambda: {"net": 0.0, "gross": 0.0, "count": 0})
    taxes, net, gross, outstanding, returns, overdue, count = (0.0,) * 7
    by_stream = {stream: 0.0 for stream in (*STREAMS, "Unclassified")}
    today = getdate(nowdate())
    classified = classifications(invoices, company, frappe.get_meta("Sales Invoice"))
    for r in invoices:
        signed_net = flt(r.base_net_total)
        signed_gross = flt(r.base_grand_total)
        tax = flt(r.base_total_taxes_and_charges)
        # Submitted return invoices are negative in ERPNext; don't subtract again.
        by_stream[classified[r["name"]][0]] += signed_net
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
    show_delivery = str(include_delivery).lower() in ("1", "true")
    notes = [
        "Revenue uses submitted Sales Invoices dated in the selected period; returns preserve their accounting sign.",
        "Outstanding and overdue show current unpaid amounts for invoices in this period.",
        "Received payments are submitted Receive-type Payment Entries in the period and may include advances.",
    ]
    if show_delivery:
        notes.append("Delivery counts cover a sample of up to 200 recent authorized jobs.")
    return {"company": company, "currency": frappe.get_cached_value("Company", company, "default_currency") or "BDT",
            "start_date": str(start), "end_date": str(end), "invoice_count": int(count),
            "net_revenue": round(net, 2), "gross_invoiced": round(gross, 2),
            "taxes": round(taxes, 2), "returns_gross": round(returns, 2),
            "revenue_by_stream": [{"stream": key, "net_revenue": round(value, 2)}
                                  for key, value in by_stream.items()],
            "invoice_outstanding_current": round(outstanding, 2),
            "invoice_overdue_current": round(overdue, 2),
            "received_payments": None if collections is None else round(collections, 2),
            "payment_count": payment_count, "daily": series,
            "financial_totals": _invoice_financial_totals(company, start, end),
            "delivery": _delivery(company) if show_delivery else None, "notes": notes}


@frappe.whitelist(methods=["GET"])
def get_invoice_documents(doctype="Sales Invoice", docstatus=None, start_date=None, end_date=None, q="", page=1, revenue_stream=None):
    if doctype not in ("Sales Invoice", "POS Invoice"):
        frappe.throw("Select Sales Invoice or POS Invoice.")
    _need(doctype)
    company = _company()
    size = 50
    try:
        page = max(1, int(page or 1))
    except (TypeError, ValueError):
        frappe.throw("Enter a valid page number.")
    try:
        start = date.fromisoformat(str(start_date)) if start_date else None
        end = date.fromisoformat(str(end_date)) if end_date else None
    except (TypeError, ValueError):
        frappe.throw("Enter valid posting dates.")
    if start and end and start > end:
        frappe.throw("From Date must not be after To Date.")

    filters = [["company", "=", company]]
    if docstatus not in (None, ""):
        if str(docstatus) not in ("0", "1", "2"):
            frappe.throw("Select Draft, Submitted or Cancelled.")
        filters.append(["docstatus", "=", int(docstatus)])
    if start:
        filters.append(["posting_date", ">=", str(start)])
    if end:
        filters.append(["posting_date", "<=", str(end)])

    meta = frappe.get_meta(doctype)
    sales_invoice = doctype == "Sales Invoice"
    if revenue_stream and (not sales_invoice or revenue_stream not in (*STREAMS, "Unclassified")):
        frappe.throw("Select a valid Sales Invoice revenue stream.")
    fields = ["name", "posting_date", "customer", "docstatus", "currency", "grand_total"]
    fields.extend(field for field in ("customer_name", "status", "is_return", "custom_service_job")
                  if meta.has_field(field))
    if sales_invoice:
        fields.append("outstanding_amount")
    output_fields = fields.copy()
    if sales_invoice:
        fields = list(dict.fromkeys([*fields, *classification_fields(meta)]))
    query = str(q or "").strip()[:90]
    or_filters = None
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        or_filters = [[doctype, field, "like", f"%{escaped}%"]
                      for field in ("name", "customer", "customer_name", "custom_service_job") if field in fields]
    query_options = {
        "fields": fields, "filters": filters, "or_filters": or_filters,
        "order_by": "posting_date desc, creation desc, name desc",
    }
    offset = (page - 1) * size
    if revenue_stream:
        rows = _stream_page(company, meta, query_options, revenue_stream, offset, size)
    else:
        rows = frappe.get_list(doctype, **query_options, limit_start=offset, limit_page_length=size + 1)
        if sales_invoice:
            _label_rows(rows, company, meta)
    output_fields += ["revenue_stream", "revenue_basis"] if sales_invoice else []
    from servicing_os.api.invoice_payment import can_receive

    income = _invoice_income_summary(company, meta, query_options, docstatus, revenue_stream) if sales_invoice else None
    summarized = sales_invoice and (docstatus in (None, "") or str(docstatus) == "1")
    daily = None
    totals = _invoice_financial_totals(company, start, end, include_daily=summarized)
    if income is not None:
        invoice_days = income.pop("daily")
        if summarized:
            daily = _daily_income_rows(invoice_days, totals.pop("daily"), bool(query or revenue_stream))

    return {
        "company": company, "rows": [{field: row.get(field) for field in output_fields} for row in rows[:size]],
        "page": page, "page_size": size, "has_next": len(rows) > size,
        "income_summary": {**income, "daily": daily} if income is not None else None,
        "financial_totals": totals,
        "can_label_stream": sales_invoice and meta.has_field(REPORT_STREAM_FIELD) and can_label(),
        "can_receive_payment": sales_invoice and can_receive(),
    }


def _period_invoice_total(doctype, company, dates, daily=False):
    if not frappe.has_permission(doctype, "read"):
        return None
    group = "posting_date" if daily else "company"
    rows = frappe.get_list(
        doctype, filters=[["company", "=", company], ["docstatus", "=", 1], *dates],
        fields=[*(["posting_date"] if daily else []), "sum(base_net_total) as net_amount"],
        group_by=group, order_by=f"{group} asc", limit_page_length=0 if daily else 1,
    )
    if daily:
        return {str(row["posting_date"]): Decimal(str(row.get("net_amount") or 0)) for row in rows}
    return flt(rows[0].get("net_amount")) if rows else 0.0


def _period_profit(company, dates, daily=False):
    if not all(frappe.has_permission(doctype, "read") for doctype in ("Account", "GL Entry")):
        return None, None
    accounts = frappe.get_list(
        "Account", filters={"company": company, "report_type": "Profit and Loss", "is_group": 0},
        fields=["name", "account_type"], order_by="name asc", limit_page_length=0,
    )
    if not accounts:
        return None, None
    kinds = {row["name"]: row["account_type"] for row in accounts}
    balances = frappe.get_list(
        "GL Entry",
        filters=[["company", "=", company], ["is_cancelled", "=", 0], ["is_opening", "!=", "Yes"],
                 ["voucher_type", "!=", "Period Closing Voucher"], ["account", "in", list(kinds)], *dates],
        fields=["account", *(["posting_date"] if daily else []),
                "sum(debit) as total_debit", "sum(credit) as total_credit"],
        group_by="posting_date, account" if daily else "account",
        order_by="posting_date asc, account asc" if daily else "account asc",
        limit_page_length=0 if daily else len(kinds),
    )
    if not balances:
        return None, None
    costs = defaultdict(Decimal)
    profits = defaultdict(Decimal)
    for row in balances:
        day = str(row["posting_date"]) if daily else ""
        net = Decimal(str(row.get("total_credit") or 0)) - Decimal(str(row.get("total_debit") or 0))
        profits[day] += net
        if kinds[row["account"]] == "Cost of Goods Sold":
            costs[day] -= net
    has_cogs_account = "Cost of Goods Sold" in kinds.values()
    if daily:
        return ({day: costs[day] for day in profits} if has_cogs_account else None), profits
    return float(costs[""]) if has_cogs_account else None, float(profits[""])


def _invoice_financial_totals(company, start, end, include_daily=False):
    dates = []
    if start:
        dates.append(["posting_date", ">=", str(start)])
    if end:
        dates.append(["posting_date", "<=", str(end)])
    cogs, profit = _period_profit(company, dates, daily=include_daily)
    purchases = _period_invoice_total("Purchase Invoice", company, dates, daily=include_daily)
    totals = {
        "currency": frappe.get_cached_value("Company", company, "default_currency"),
        "start_date": str(start) if start else None,
        "end_date": str(end) if end else None,
        "purchases": purchases,
        "sales": _period_invoice_total("Sales Invoice", company, dates),
        "cogs": cogs,
        "profit": profit,
    }
    if include_daily:
        totals["daily"] = {"purchases": purchases, "cogs": cogs, "profit": profit}
        for key in totals["daily"]:
            values = totals["daily"][key]
            totals[key] = float(sum(values.values())) if values is not None else None
    return totals


def _daily_income_rows(invoice_days, company_days, matching_dates_only):
    days = set(invoice_days)
    if not matching_dates_only:
        for series in company_days.values():
            days.update(series or {})
    result = []
    for day in sorted(days, reverse=True):
        sales = invoice_days.get(day, {})
        row = {"date": day, "sales": float(sales.get("sales", 0)), "count": sales.get("count", 0)}
        for key, values in company_days.items():
            value = values.get(day, 0 if key == "purchases" else None) if values is not None else None
            row[key] = float(value) if value is not None else None
        result.append(row)
    return result


def _label_rows(rows, company, meta):
    classified = classifications(rows, company, meta)
    for row in rows:
        row["revenue_stream"], row["revenue_basis"] = classified[row["name"]]


def _invoice_income_summary(company, meta, query_options, docstatus, stream):
    amounts = dict.fromkeys((stream,) if stream else (*STREAMS, "Unclassified"), Decimal("0"))
    count = 0
    daily = defaultdict(lambda: {"sales": Decimal("0"), "count": 0})
    if docstatus in (None, "") or str(docstatus) == "1":
        filters = [condition for condition in query_options["filters"] if condition[0] != "docstatus"]
        filters.append(["docstatus", "=", 1])
        fields = list(dict.fromkeys(["name", "posting_date", "base_net_total", "is_return", *classification_fields(meta)]))
        start = 0
        batch_size = 500
        while True:
            rows = frappe.get_list(
                "Sales Invoice", fields=fields, filters=filters, or_filters=query_options["or_filters"],
                order_by=query_options["order_by"], limit_start=start, limit_page_length=batch_size,
            )
            labelled = classifications(rows, company, meta)
            for row in rows:
                label = labelled[row["name"]][0]
                if label in amounts:
                    amount = Decimal(str(row.get("base_net_total") or 0))
                    amounts[label] += amount
                    count += 1
                    if row.get("posting_date"):
                        day = daily[str(row["posting_date"])]
                        day["sales"] += amount
                        day["count"] += 1
            if len(rows) < batch_size:
                break
            start += batch_size
    return {
        "currency": frappe.get_cached_value("Company", company, "default_currency"),
        "invoice_count": count,
        "streams": {label: float(amount) for label, amount in amounts.items()},
        "total": float(sum(amounts.values())),
        "daily": dict(daily),
    }


def _stream_page(company, meta, query_options, stream, offset, size):
    # Classify before applying the requested page. Legacy matches may be anywhere
    # in the date range; fetch in batches so the full register is never held in memory.
    matching = []
    start = 0
    skipped = 0
    batch_size = 250
    while len(matching) <= size:
        batch = frappe.get_list("Sales Invoice", **query_options, limit_start=start, limit_page_length=batch_size)
        _label_rows(batch, company, meta)
        for row in batch:
            if row["revenue_stream"] != stream:
                continue
            if skipped < offset:
                skipped += 1
                continue
            matching.append(row)
            if len(matching) > size:
                break
        if len(batch) < batch_size:
            break
        start += batch_size
    return matching


@frappe.whitelist(methods=["POST"])
def set_reporting_stream(invoice_name, revenue_stream=None):
    if not can_label():
        frappe.throw("Permission to update invoice reporting labels is required.", frappe.PermissionError)
    if revenue_stream not in (*STREAMS, "", None):
        frappe.throw("Choose a valid revenue stream.")
    name = str(invoice_name or "").strip()
    if not name or len(name) > 140:
        frappe.throw("Choose an invoice.")
    company = _company()
    if not frappe.get_meta("Sales Invoice").has_field(REPORT_STREAM_FIELD):
        frappe.throw("Run bench migrate to install the historical reporting field.")
    frappe.db.sql("select name from `tabSales Invoice` where name=%s for update", (name,))
    invoice = frappe.get_doc("Sales Invoice", name)
    invoice.check_permission("read")
    invoice.check_permission("write")
    if invoice.company != company or cint(invoice.docstatus) != 1:
        frappe.throw("Select a submitted Sales Invoice from the active shop.")
    row = invoice.as_dict()
    current, basis = classifications([row], company, invoice.meta)[name]
    if basis not in ("manual", "unclassified"):
        frappe.throw("This invoice already has a revenue stream from its saved source.")
    new = revenue_stream or None
    if invoice.get(REPORT_STREAM_FIELD) != new:
        # Change one report field only. Do not run Sale Invoice posting hooks.
        frappe.db.set_value("Sales Invoice", name, REPORT_STREAM_FIELD, new)
        invoice.add_comment("Info", text=f"Historical reporting stream changed from {current} to {new or 'Unclassified'}.")
    return {"name": name, "revenue_stream": new or "Unclassified"}


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
            "currency": frappe.get_cached_value("Company", company, "default_currency") or "BDT",
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
