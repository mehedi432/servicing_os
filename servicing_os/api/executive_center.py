"""Manager's read-only action center for SERVICING OS.

This is an operational exception queue, not a replacement for ERPNext General
Ledger, P&L, Accounts Receivable, Stock Ledger, or standard POS reports.
"""
import frappe
from frappe.utils import nowdate
from datetime import date

COMPANY = "AL MODINA COMPUTERS LIMITED"
WAREHOUSE = "Spare Parts - AMCL"
ROLES = {"System Manager", "Accounts Manager"}
TERMINAL = ("Delivered", "Cancelled")


def _authorize():
    user = frappe.session.user
    if user != "Administrator" and not ROLES.intersection(set(frappe.get_roles(user))):
        frappe.throw("Executive reports require Manager/Accounts access.", frappe.PermissionError)
    for dt in ("Service Job", "Sales Invoice", "Material Request", "Item", "Warehouse", "Payment Entry"):
        if not frappe.has_permission(dt, "read"):
            frappe.throw("Missing read permission for " + dt, frappe.PermissionError)
    if not frappe.get_meta("Sales Invoice").has_field("custom_service_job"):
        frappe.throw("Sales Invoice custom_service_job Link missing (Step 6.16A).")
    if not frappe.get_meta("Material Request").has_field("custom_service_job"):
        frappe.throw("Material Request custom_service_job Link missing (Step 6.15C).")


def _dates(start_value, end_value):
    today = date.fromisoformat(nowdate())
    try:
        start = date.fromisoformat(str(start_value)) if start_value else today.replace(day=1)
        end = date.fromisoformat(str(end_value)) if end_value else today
    except (TypeError, ValueError):
        frappe.throw("Dates must be YYYY-MM-DD.")
    if start > end or (end - start).days > 365:
        frappe.throw("Select a valid period of up to 366 days.")
    return str(start), str(end)


def _sql(sql, params):
    return [dict(r) for r in frappe.db.sql(sql, params, as_dict=True)]


def _count_and_rows(from_clause, columns, where_clause, params, ordering, limit=8):
    """Identical conditions for totals and bounded drilldown; SQL is static."""
    total = frappe.db.sql(
        "SELECT COUNT(*) AS n " + from_clause + " WHERE " + where_clause,
        params, as_dict=True,
    )[0].n or 0
    data = _sql(
        "SELECT " + columns + " " + from_clause + " WHERE " + where_clause
        + " ORDER BY " + ordering + " LIMIT " + str(int(limit)),
        params,
    )
    return {"count": int(total), "rows": data, "truncated": int(total) > len(data)}


@frappe.whitelist(methods=["GET"])
def get_executive_center(from_date=None, to_date=None):
    """Read-only owner priorities, plus existing official-source summary."""
    _authorize()
    start, end = _dates(from_date, to_date)
    # Avoid a second interpretation of sales/collections. The owner dashboard
    # uses posted invoices/payment allocations and clearly states their basis.
    from servicing_os.api.owner_reports import get_owner_dashboard
    overview = get_owner_dashboard(from_date=start, to_date=end)
    p = {"company": COMPANY, "warehouse": WAREHOUSE}

    jobs_from = "FROM `tabService Job` sj"
    active = "sj.status NOT IN ('Delivered', 'Cancelled')"
    unassigned = _count_and_rows(
        jobs_from,
        "sj.name AS service_job, sj.status, sj.customer_name, sj.device_type, sj.brand, sj.device_model, sj.received_date",
        active + " AND (sj.technician IS NULL OR sj.technician = '')",
        p, "sj.received_date ASC, sj.name ASC",
    )
    aging = _count_and_rows(
        jobs_from,
        "sj.name AS service_job, sj.status, sj.customer_name, sj.technician, sj.received_date, "
        "TIMESTAMPDIFF(DAY, sj.received_date, NOW()) AS age_days",
        active + " AND sj.received_date IS NOT NULL "
        "AND TIMESTAMPDIFF(DAY, sj.received_date, NOW()) >= 7",
        p, "sj.received_date ASC, sj.name ASC",
    )
    # A manager can review billing from Completed onward. Draft invoices
    # go in their own queue rather than being counted as missing invoices.
    billing_from = jobs_from
    billing_base = "sj.status IN ('Completed', 'Ready to Deliver', 'Delivered')"
    no_invoice = """NOT EXISTS (
        SELECT 1 FROM `tabSales Invoice` si
         WHERE si.company = %(company)s AND si.custom_service_job = sj.name
           AND si.is_return = 0 AND si.docstatus IN (0, 1)
    )"""
    billing = _count_and_rows(
        billing_from,
        "sj.name AS service_job, sj.status, sj.customer_name, sj.technician, sj.received_date",
        billing_base + " AND " + no_invoice,
        p, "sj.received_date ASC, sj.name ASC",
    )
    draft_inv = _count_and_rows(
        "FROM `tabSales Invoice` si",
        "si.name AS invoice, si.custom_service_job AS service_job, si.customer_name, si.posting_date, si.base_grand_total AS amount",
        "si.company = %(company)s AND si.docstatus = 0 AND si.is_return = 0 "
        "AND si.custom_service_job IS NOT NULL AND si.custom_service_job != ''",
        p, "si.creation ASC, si.name ASC",
    )
    dues = _count_and_rows(
        "FROM `tabSales Invoice` si",
        "si.name AS invoice, si.custom_service_job AS service_job, si.customer_name, "
        "si.due_date, si.outstanding_amount AS amount",
        "si.company = %(company)s AND si.docstatus = 1 AND si.is_return = 0 "
        "AND si.outstanding_amount > 0 AND si.custom_service_job IS NOT NULL "
        "AND si.custom_service_job != ''",
        p, "si.due_date ASC, si.name ASC",
    )
    # A submitted Material Request does NOT necessarily mean nothing has been
    # issued. We label these as requests for stock-status review, not "unissued".
    stock_requests = _count_and_rows(
        "FROM `tabMaterial Request` mr",
        "mr.name AS material_request, mr.custom_service_job AS service_job, "
        "mr.transaction_date, mr.status",
        "mr.company = %(company)s AND mr.docstatus = 1 "
        "AND mr.material_request_type = 'Material Issue' "
        "AND mr.status NOT IN ('Issued', 'Stopped', 'Cancelled') "
        "AND mr.custom_service_job IS NOT NULL AND mr.custom_service_job != ''",
        p, "mr.transaction_date ASC, mr.name ASC",
    )
    # Catalog items with zero/negative Bin balance; neither purchase orders
    # nor stock reservations are implied. No valuation assumed.
    empty_stock = _count_and_rows(
        "FROM `tabItem` i LEFT JOIN `tabBin` b "
        "ON b.item_code = i.name AND b.warehouse = %(warehouse)s",
        "i.name AS item_code, i.item_name, COALESCE(b.actual_qty,0) AS actual_qty",
        "i.disabled = 0 AND i.is_sales_item = 1 AND i.is_stock_item = 1 "
        "AND COALESCE(b.actual_qty,0) <= 0",
        p, "i.item_name ASC, i.name ASC",
    )

    return {
        "company": COMPANY,
        "warehouse": WAREHOUSE,
        "currency": "BDT",
        "from_date": start,
        "to_date": end,
        "overview": {
            "received_in_period": overview["service_jobs"]["received_in_period"],
            "revenue_ex_tax_bdt": overview["billing"]["revenue_ex_tax_bdt"],
            "allocated_collections_bdt": overview["collections"]["allocated_to_service_invoices_bdt"],
            "outstanding_now_all_dates_bdt": overview["billing"]["current_outstanding_all_dates_bdt"],
            "stock_on_hand_units_now": overview["stock_now"]["on_hand_units"],
        },
        "queues": {
            "unassigned": unassigned,
            "aging_7_days": aging,
            "ready_unbilled": billing,
            "draft_invoices": draft_inv,
            "customer_dues": dues,
            "parts_requests_review": stock_requests,
            "out_of_stock_catalog": empty_stock,
        },
        "basis": {
            "period": "Received jobs by received date, revenue by invoice posting date and collections by payment posting date.",
            "current": "All attention queues and current receivables are as of now (not limited to the date filter).",
            "accounting": "Revenue is posted invoice revenue ex tax; collections are Payment Entry allocations; current dues are NOT revenue.",
            "inventory": "Zero-quantity catalog items are not automatically urgent; verify stock policy and demand.",
            "profit": "This is not net profit. Use ERPNext Profit and Loss and the separate contribution report.",
        },
    }
