"""Owner reports for AMCL. Read-only ERPNext documents; no ledger posting.

Period service jobs are grouped by RECEIVED date and current status (not historical
status change date). Invoice revenue is based on submitted invoice POSTING dates.
Collections are submitted Payment Entry allocations to AMCL repair invoices by
PAYMENT posting date. Current dues include all historical open service invoices.
"""
import frappe
from frappe.utils import getdate, nowdate, get_first_day, add_days

COMPANY = "AL MODINA COMPUTERS LIMITED"
CURRENCY = "BDT"
WAREHOUSE = "Spare Parts - AMCL"
SERVICE_LINK = "custom_service_job"
MANAGER_ROLES = {"System Manager", "Accounts Manager"}


def _check_access():
    user = frappe.session.user
    if user != 'Administrator' and not MANAGER_ROLES.intersection(frappe.get_roles(user)):
        frappe.throw('Owner reports require Administrator, System Manager or Accounts Manager.',
                     frappe.PermissionError)
    for doctype in ('Service Job', 'Sales Invoice', 'Payment Entry', 'Item', 'Warehouse'):
        if not frappe.has_permission(doctype, 'read'):
            frappe.throw('Read permission missing: ' + doctype, frappe.PermissionError)


def _range(from_date=None, to_date=None):
    try:
        start = getdate(from_date or get_first_day(nowdate()))
        end = getdate(to_date or nowdate())
    except (TypeError, ValueError):
        frappe.throw('Use valid YYYY-MM-DD dates.')
    if end < start:
        frappe.throw('To Date must not be earlier than From Date.')
    if (end - start).days > 365:
        frappe.throw('Choose a date range of at most 366 calendar days.')
    return str(start), str(end), str(add_days(end, 1))


def _one(sql, args):
    return (frappe.db.sql(sql, args, as_dict=True) or [{}])[0]


@frappe.whitelist(methods=['GET'])
def get_owner_dashboard(from_date=None, to_date=None):
    """Consolidated overview. NO inserts, saves, commits or submits."""
    _check_access()
    if not frappe.get_meta('Sales Invoice').has_field(SERVICE_LINK):
        frappe.throw('Sales Invoice Service Job link missing; install Step 6.16A first.')
    start, end, end_exclusive = _range(from_date, to_date)
    args = {'company': COMPANY, 'start': start, 'end': end,
            'end_exclusive': end_exclusive, 'warehouse': WAREHOUSE,
            'currency': CURRENCY}

    # Service Jobs received IN the date range, grouped by their CURRENT statuses.
    stage_rows = frappe.db.sql("""
        SELECT COALESCE(NULLIF(status, ''), 'Unknown') AS status, COUNT(*) AS qty
          FROM `tabService Job`
         WHERE received_date >= %(start)s
           AND received_date < %(end_exclusive)s
         GROUP BY status ORDER BY qty DESC, status ASC
    """, args, as_dict=True)
    stage_counts = {r.status: int(r.qty) for r in stage_rows}
    jobs_total = sum(stage_counts.values())

    # Current technician backlog across ALL receipt dates, NOT "period completed".
    backlog = frappe.db.sql("""
        SELECT sj.technician AS user_id,
               COALESCE(NULLIF(u.full_name, ''), sj.technician, 'Unassigned') AS technician,
               COUNT(*) AS active_jobs,
               SUM(CASE WHEN sj.status = 'Completed' THEN 1 ELSE 0 END) AS completed_waiting,
               SUM(CASE WHEN sj.status = 'Waiting for Parts' THEN 1 ELSE 0 END) AS waiting_parts
          FROM `tabService Job` sj
          LEFT JOIN `tabUser` u ON u.name = sj.technician
         WHERE sj.status NOT IN ('Delivered', 'Cancelled')
         GROUP BY sj.technician, u.full_name
         ORDER BY active_jobs DESC, technician ASC
    """, as_dict=True)

    # Submitted repair Sales Invoices only. Credit notes reduce signed net revenue.
    invoice_finance = _one("""
        SELECT COUNT(*) AS invoices,
               COALESCE(SUM(base_net_total), 0) AS revenue_ex_tax,
               COALESCE(SUM(base_grand_total), 0) AS invoiced_incl_tax
          FROM `tabSales Invoice`
         WHERE company = %(company)s AND currency = %(currency)s
           AND docstatus = 1 AND posting_date BETWEEN %(start)s AND %(end)s
           AND custom_service_job IS NOT NULL AND custom_service_job != ''
    """, args)

    # Current amount owed for ALL submitted, non-return, BDT linked invoices,
    # regardless of invoice date. This is current receivable, not period revenue.
    dues = _one("""
        SELECT COUNT(*) AS open_invoices,
               COALESCE(SUM(outstanding_amount), 0) AS due_now
          FROM `tabSales Invoice`
         WHERE company = %(company)s AND currency = %(currency)s
           AND docstatus = 1 AND is_return = 0 AND outstanding_amount > 0
           AND custom_service_job IS NOT NULL AND custom_service_job != ''
    """, args)

    # Amount allocated to submitted BDT service invoices by submitted Receive
    # Payment Entries during the selected period. Excludes draft/unallocated advances.
    receipts = _one("""
        SELECT COALESCE(SUM(r.allocated_amount), 0) AS allocated_receipts,
               COALESCE(SUM(CASE WHEN pe.mode_of_payment = 'Cash'
                                 THEN r.allocated_amount ELSE 0 END), 0) AS cash_allocated,
               COUNT(DISTINCT pe.name) AS payment_entries
          FROM `tabPayment Entry` pe
          INNER JOIN `tabPayment Entry Reference` r
                  ON r.parent = pe.name AND r.parenttype = 'Payment Entry'
          INNER JOIN `tabSales Invoice` si
                  ON si.name = r.reference_name
         WHERE pe.company = %(company)s AND pe.docstatus = 1
           AND pe.payment_type = 'Receive'
           AND pe.posting_date BETWEEN %(start)s AND %(end)s
           AND r.reference_doctype = 'Sales Invoice'
           AND si.company = %(company)s AND si.currency = %(currency)s
           AND si.docstatus = 1
           AND si.custom_service_job IS NOT NULL AND si.custom_service_job != ''
    """, args)

    # Approved but pending parts requests, date range based on request date.
    requests = _one("""
        SELECT COALESCE(SUM(CASE WHEN docstatus = 0 THEN 1 ELSE 0 END), 0) AS drafts,
               COALESCE(SUM(CASE WHEN docstatus = 1
                     AND status NOT IN ('Issued','Stopped','Cancelled')
                       THEN 1 ELSE 0 END), 0) AS submitted_pending
          FROM `tabMaterial Request`
         WHERE company = %(company)s
           AND material_request_type = 'Material Issue'
           AND transaction_date BETWEEN %(start)s AND %(end)s
           AND custom_service_job IS NOT NULL AND custom_service_job != ''
    """, args)

    # Stock is a current balance at the single dedicated warehouse, not a
    # calculated expense/revenue and not date-filtered.
    stock = _one("""
        SELECT COUNT(*) AS stocked_skus,
               COALESCE(SUM(b.actual_qty), 0) AS quantity_on_hand,
               COALESCE(SUM(b.reserved_qty), 0) AS reserved_quantity
          FROM `tabBin` b
          INNER JOIN `tabItem` i ON i.name = b.item_code
         WHERE b.warehouse = %(warehouse)s
           AND i.is_stock_item = 1 AND i.is_sales_item = 1 AND i.disabled = 0
    """, args)

    # Small drilldown. Summary calculations above are not truncated to this list.
    recent = frappe.db.sql("""
        SELECT name, posting_date, customer, custom_service_job AS service_job,
               base_net_total AS revenue_ex_tax, outstanding_amount, is_return
          FROM `tabSales Invoice`
         WHERE company = %(company)s AND currency = %(currency)s
           AND docstatus = 1
           AND posting_date BETWEEN %(start)s AND %(end)s
           AND custom_service_job IS NOT NULL AND custom_service_job != ''
         ORDER BY posting_date DESC, creation DESC LIMIT 30
    """, args, as_dict=True)

    return {
        'company': COMPANY, 'currency': CURRENCY,
        'from_date': start, 'to_date': end,
        'service_jobs': {'received_in_period': jobs_total,
                         'current_stage_for_received_jobs': stage_counts},
        'technicians': [{
            'user_id': row.user_id,
            'technician': row.technician,
            'active_jobs': int(row.active_jobs or 0),
            'completed_waiting': int(row.completed_waiting or 0),
            'waiting_parts': int(row.waiting_parts or 0),
        } for row in backlog],
        'billing': {
            'submitted_invoices_in_period': int(invoice_finance.invoices or 0),
            'revenue_ex_tax_bdt': float(invoice_finance.revenue_ex_tax or 0),
            'invoiced_incl_tax_bdt': float(invoice_finance.invoiced_incl_tax or 0),
            'current_outstanding_all_dates_bdt': float(dues.due_now or 0),
            'current_open_invoices_all_dates': int(dues.open_invoices or 0),
        },
        'collections': {
            'allocated_to_service_invoices_bdt': float(receipts.allocated_receipts or 0),
            'cash_allocated_to_service_invoices_bdt': float(receipts.cash_allocated or 0),
            'submitted_payment_entries': int(receipts.payment_entries or 0),
        },
        'parts_requests': {
            'drafts_in_period': int(requests.drafts or 0),
            'submitted_pending_in_period': int(requests.submitted_pending or 0),
        },
        'stock_now': {
            'warehouse': WAREHOUSE,
            'skus_with_bin': int(stock.stocked_skus or 0),
            'on_hand_units': float(stock.quantity_on_hand or 0),
            'reserved_units': float(stock.reserved_quantity or 0),
        },
        'recent_submitted_invoices': recent,
        'basis': {
            'service_jobs': 'Jobs received within the selected dates, grouped by CURRENT status.',
            'technicians': 'Currently assigned, non-delivered, non-cancelled jobs across all dates.',
            'revenue': 'Submitted BDT repair invoices by invoice posting date, net of returns, before tax.',
            'collections': 'Submitted Receive Payment Entry allocations by payment posting date; unallocated advances, POS and journal adjustments excluded.',
            'dues': 'Current outstanding BDT repair invoices across all posting dates, not period dues.',
            'stock': 'Current warehouse quantities from ERPNext Bin; not date-filtered.',
            'profit': 'Not calculated here. Use Step 6.16A contribution report and ERPNext Profit and Loss for appropriate purposes.',
        },
    }
