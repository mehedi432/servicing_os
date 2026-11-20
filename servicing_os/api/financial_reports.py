"""AMCL financial/repair contribution views. All endpoints are read-only.

Sales: submitted invoice net revenue ex tax (invoice posting date).
Collections: submitted Receive Payment Entry allocations (payment posting date).
Dues: current outstanding amount, selected by invoice posting date.
Contribution: repair invoice item net revenue less verified Stock Ledger issue
cost, BEFORE technician labor cost, overhead and other expenses.
Not a replacement for ERPNext General Ledger or Profit and Loss.
"""
from datetime import date, timedelta
import frappe
from frappe.utils import flt, nowdate
from servicing_os.api.site_company_706 import cash_account, current_company, current_currency

LABOR_ITEM = "AMCL-REPAIR-LABOR"
JOB_FIELD = "custom_service_job"
ACCESS_ROLES = {"System Manager", "Accounts Manager"}
REPORTS = {"sales", "collections", "dues", "contribution"}


def _access(report):
    user = frappe.session.user
    if user != "Administrator" and not ACCESS_ROLES.intersection(set(frappe.get_roles(user))):
        frappe.throw("Owner/Accounts Manager access required.", frappe.PermissionError)
    if not frappe.has_permission("Sales Invoice", "read"):
        frappe.throw("Sales Invoice read permission required.", frappe.PermissionError)
    if report == "collections" and not frappe.has_permission("Payment Entry", "read"):
        frappe.throw("Payment Entry read permission required.", frappe.PermissionError)
    if report == "contribution" and not frappe.has_permission("Stock Entry", "read"):
        frappe.throw("Stock Entry read permission required.", frappe.PermissionError)
    if not frappe.get_meta("Sales Invoice").has_field(JOB_FIELD):
        frappe.throw("Sales Invoice Service Job link is missing (Step 6.16A).")


def _period(start_value, end_value):
    today = date.fromisoformat(nowdate())
    try:
        start = date.fromisoformat(str(start_value)) if start_value else today.replace(day=1)
        end = date.fromisoformat(str(end_value)) if end_value else today
    except (ValueError, TypeError):
        frappe.throw("Dates must use YYYY-MM-DD.")
    if start > end or (end - start).days > 366:
        frappe.throw("Choose a valid period of at most 367 days.")
    return str(start), str(end)


def _limit(value):
    try:
        result = int(value)
    except (TypeError, ValueError):
        frappe.throw("Invalid report row limit.")
    if result < 1 or result > 300:
        frappe.throw("Row limit must be between 1 and 300.")
    return result


def _money(value):
    return round(flt(value), 2)


def _result(report, start, end, total, rows, summary, note, page_limit):
    return {
        "report": report, "company": current_company(), "currency": current_currency(),
        "from_date": start, "to_date": end,
        "total": int(total or 0), "limit": page_limit,
        "truncated": int(total or 0) > page_limit,
        "rows": rows, "summary": summary, "note": note,
    }


@frappe.whitelist(methods=["GET"])
def get_financial_report(report="sales", from_date=None, to_date=None, limit=200):
    """Read-only finance views using standard submitted ERPNext transactions."""
    report = str(report or "sales").strip()
    if report not in REPORTS:
        frappe.throw("Unknown financial report.")
    _access(report)
    start, end = _period(from_date, to_date)
    page_limit = _limit(limit)
    params = {"company": current_company(), "currency": current_currency(),
              "start": start, "end": end, "limit": page_limit}

    # Period selection uses invoice posting date for sales, dues and contribution;
    # collection uses the receipt's own posting date. Each scope excludes
    # unrelated company sales and invoices that are not linked to Service Jobs.
    invoice_filter = """si.company = %(company)s AND si.docstatus = 1
        AND si.currency = %(currency)s
        AND si.custom_service_job IS NOT NULL AND si.custom_service_job != ''
        AND si.posting_date BETWEEN %(start)s AND %(end)s"""

    if report == "sales":
        row = frappe.db.sql("""
            SELECT COUNT(*) AS n, COALESCE(SUM(si.base_net_total),0) AS net,
                   COALESCE(SUM(si.base_grand_total),0) AS gross,
                   COALESCE(SUM(CASE WHEN si.is_return=0
                     THEN si.outstanding_amount ELSE 0 END),0) AS outstanding_now
              FROM `tabSales Invoice` si WHERE """ + invoice_filter,
            params, as_dict=True)[0]
        entries = frappe.db.sql("""
            SELECT si.name AS invoice, si.posting_date, si.custom_service_job AS service_job,
                   si.customer, si.customer_name, si.status, si.is_return,
                   si.base_net_total AS net_sales, si.base_grand_total AS grand_total,
                   CASE WHEN si.is_return=0 THEN si.outstanding_amount ELSE NULL END AS outstanding_now
              FROM `tabSales Invoice` si WHERE """ + invoice_filter + """
             ORDER BY si.posting_date DESC, si.name DESC LIMIT %(limit)s""",
            params, as_dict=True)
        rows = [dict(x) for x in entries]
        for item in rows:
            for field in ("net_sales", "grand_total"):
                item[field] = _money(item[field])
            if item["outstanding_now"] is not None:
                item["outstanding_now"] = _money(item["outstanding_now"])
        return _result(report, start, end, row.n, rows,
            {"net_sales_ex_tax": _money(row.net),
             "gross_including_tax": _money(row.gross),
             "outstanding_now": _money(row.outstanding_now)},
            "Submitted company-currency repair invoices and linked credit notes, by invoice posting date. "
            "Outstanding is current, not historical. Unlinked credit notes, write-offs "
            "and other ledger adjustments need reconciliation in ERPNext.", page_limit)

    if report == "collections":
        params["cash_account"] = cash_account()
        # A Payment Entry can allocate to multiple Sales Invoices. List allocations,
        # not the whole paid amount, to avoid over-attributing receipts to repairs.
        query = """
            FROM `tabPayment Entry` pe
            INNER JOIN `tabPayment Entry Reference` per
              ON per.parent=pe.name AND per.parenttype='Payment Entry'
            INNER JOIN `tabSales Invoice` si
              ON si.name=per.reference_name
            WHERE pe.docstatus=1 AND pe.payment_type='Receive'
              AND pe.company=%(company)s
              AND pe.posting_date BETWEEN %(start)s AND %(end)s
              AND per.reference_doctype='Sales Invoice'
              AND si.docstatus=1 AND si.company=%(company)s
              AND si.currency=%(currency)s
              AND si.custom_service_job IS NOT NULL AND si.custom_service_job != ''
        """
        summary = frappe.db.sql("""
            SELECT COUNT(*) AS n,
              COALESCE(SUM(per.allocated_amount),0) AS allocated,
              COALESCE(SUM(CASE WHEN pe.paid_to=%(cash_account)s
                 THEN per.allocated_amount ELSE 0 END),0) AS cash_allocated
        """ + query, params, as_dict=True)[0]
        entries = frappe.db.sql("""
            SELECT pe.name AS payment_entry, pe.posting_date,
                   pe.mode_of_payment, pe.paid_to,
                   si.custom_service_job AS service_job, si.name AS invoice,
                   si.customer, per.allocated_amount AS allocated_amount
        """ + query + """
            ORDER BY pe.posting_date DESC, pe.name DESC, si.name DESC
            LIMIT %(limit)s""", params, as_dict=True)
        rows = [dict(x) for x in entries]
        for item in rows:
            item["allocated_amount"] = _money(item["allocated_amount"])
        return _result(report, start, end, summary.n, rows,
            {"allocated_to_repairs": _money(summary.allocated),
             "allocated_to_cash_account": _money(summary.cash_allocated)},
            "Submitted customer Receive Payment Entry allocations to company-currency repair invoices, "
            "dated by PAYMENT posting date. Excludes unallocated advances, Journal Entries, "
            "payment reconciliations not reflected in these references, and refunds. "
            "This is not a bank balance or official cash-flow report.", page_limit)

    if report == "dues":
        due_filter = invoice_filter + " AND si.is_return = 0 AND si.outstanding_amount > 0"
        summary = frappe.db.sql("""
            SELECT COUNT(*) AS n, COALESCE(SUM(si.outstanding_amount),0) AS due
              FROM `tabSales Invoice` si WHERE """ + due_filter,
            params, as_dict=True)[0]
        entries = frappe.db.sql("""
            SELECT si.name AS invoice, si.posting_date, si.due_date,
                   si.custom_service_job AS service_job,
                   si.customer, si.customer_name, si.status,
                   si.grand_total, si.outstanding_amount
              FROM `tabSales Invoice` si WHERE """ + due_filter + """
             ORDER BY si.posting_date ASC, si.name ASC LIMIT %(limit)s""",
            params, as_dict=True)
        rows = [dict(x) for x in entries]
        for item in rows:
            item["grand_total"] = _money(item["grand_total"])
            item["outstanding_amount"] = _money(item["outstanding_amount"])
        return _result(report, start, end, summary.n, rows,
            {"current_outstanding": _money(summary.due)},
            "Current outstanding on submitted company-currency repair invoices posted in the selected "
            "date range. Credit notes and other allocations can change current dues. "
            "For official receivables and aging use ERPNext Accounts Receivable.", page_limit)

    # Job contribution: grouping billed invoices by Service Job, not treating
    # repair estimates as revenue. Issued-part cost comes from Stock Ledger;
    # missing valuations remain null rather than assumed zero.
    job_query = """
        FROM `tabSales Invoice` si
        WHERE """ + invoice_filter
    total_row = frappe.db.sql("""
        SELECT COUNT(DISTINCT si.custom_service_job) AS n
        """ + job_query, params, as_dict=True)[0]
    # MariaDB does not support LIMIT inside an IN subquery on some versions;
    # select the bounded job set first, then fetch its invoice rows.
    chosen_jobs = frappe.db.sql("""
        SELECT si.custom_service_job AS service_job
        """ + job_query + """
        GROUP BY si.custom_service_job
        ORDER BY MIN(si.posting_date) DESC, si.custom_service_job DESC
        LIMIT %(limit)s""", params, as_dict=True)
    job_names = tuple(x.service_job for x in chosen_jobs)
    invoice_rows = []
    if job_names:
        invoice_rows = frappe.db.sql("""
            SELECT si.name AS invoice, si.custom_service_job AS service_job,
                   si.customer, si.base_net_total AS net_sales, si.posting_date
            """ + job_query + """
            AND si.custom_service_job IN %(job_names)s
            ORDER BY si.posting_date DESC, si.name DESC""",
            dict(params, job_names=job_names), as_dict=True)
    jobs = {}
    invoice_names = []
    for entry in invoice_rows:
        job = jobs.setdefault(entry.service_job, {
            "service_job": entry.service_job, "customer": entry.customer,
            "invoices": [], "net_revenue": 0.0,
            "parts_revenue": 0.0, "labor_revenue": 0.0})
        job["invoices"].append(entry.invoice)
        job["net_revenue"] += flt(entry.net_sales)
        invoice_names.append(entry.invoice)
    if invoice_names:
        grouped = frappe.db.sql("""
            SELECT sii.parent AS invoice,
               SUM(CASE WHEN sii.item_code=%(labor)s
                   THEN sii.base_net_amount ELSE 0 END) AS labor,
               SUM(CASE WHEN sii.item_code!=%(labor)s
                   THEN sii.base_net_amount ELSE 0 END) AS parts
              FROM `tabSales Invoice Item` sii
             WHERE sii.parent IN %(invoice_names)s
             GROUP BY sii.parent""",
            {"labor": LABOR_ITEM, "invoice_names": tuple(invoice_names)}, as_dict=True)
        inv_to_job = {x.invoice: x.service_job for x in invoice_rows}
        for entry in grouped:
            target = jobs[inv_to_job[entry.invoice]]
            target["labor_revenue"] += flt(entry.labor)
            target["parts_revenue"] += flt(entry.parts)
    from servicing_os.api.repair_billing import get_issued_rows
    rows = []
    for job in jobs.values():
        issued = get_issued_rows(job["service_job"])
        known = all(x.get("stock_cost") is not None for x in issued)
        cost = sum(flt(x["stock_cost"]) for x in issued) if known else None
        job["net_revenue"] = _money(job["net_revenue"])
        job["parts_revenue"] = _money(job["parts_revenue"])
        job["labor_revenue"] = _money(job["labor_revenue"])
        job["issued_parts_cost"] = _money(cost) if known else None
        job["contribution"] = _money(job["net_revenue"] - cost) if known else None
        job["cost_complete"] = bool(known)
        job["invoices"] = ", ".join(job["invoices"])
        rows.append(job)
    rows.sort(key=lambda x: x["service_job"], reverse=True)
    complete = [x for x in rows if x["cost_complete"]]
    return _result(report, start, end, total_row.n, rows,
        {"jobs_shown": len(rows), "valuation_complete_shown": len(complete),
         "contribution_known_shown": _money(sum(x["contribution"] for x in complete))},
        "Operational contribution by submitted company-currency repair invoices posted in the selected "
        "period. Issued-parts cost uses linked Stock Ledger valuation regardless of issue date. "
        "Totals apply only to displayed jobs with complete valuation. Excludes internal labor "
        "cost, overhead, taxes and unrelated GL adjustments; NOT net profit or official P&L.",
        page_limit)
