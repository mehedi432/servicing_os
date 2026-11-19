import math
import frappe
from frappe.utils import flt

# SERVICING_OS_REPAIR_BILLING_616A
COMPANY = "AL MODINA COMPUTERS LIMITED"
WAREHOUSE = "Spare Parts - AMCL"
LABOR_ITEM = "AMCL-REPAIR-LABOR"
FIELD = "custom_service_job"
MANAGER_ROLES = {"System Manager", "Accounts Manager"}


def require_manager():
    user = frappe.session.user
    if user != "Administrator" and not MANAGER_ROLES.intersection(frappe.get_roles(user)):
        frappe.throw("Accounts Manager or System Manager access required.", frappe.PermissionError)


def finite_nonnegative(value, label):
    try:
        n = float(value)
    except (ValueError, TypeError):
        frappe.throw(label + " must be a valid number")
    if not math.isfinite(n) or n < 0:
        frappe.throw(label + " must be a finite non-negative number")
    return n


def get_job(job_name):
    job = frappe.get_doc("Service Job", job_name)
    if job.get("shop") and job.shop != COMPANY:
        frappe.throw("Service Job belongs to another company")
    if not job.get("customer") or not frappe.db.exists("Customer", job.customer):
        frappe.throw("Service Job has no valid ERPNext Customer")
    if job.status == "Cancelled":
        frappe.throw("Cannot invoice a cancelled job")
    return job


def get_issued_rows(job_name):
    """Only submitted Material Issue rows linked to submitted job requests.

    Return rows and SLE-derived cost. Missing ledger cost remains unknown,
    rather than inventing zero expense.
    """
    mr_names = frappe.get_all(
        "Material Request",
        filters={"company": COMPANY, "material_request_type": "Material Issue",
                 "custom_service_job": job_name, "docstatus": 1},
        pluck="name", limit_page_length=10000,
    )
    if not mr_names:
        return []
    entries = frappe.get_all("Stock Entry", filters={
        "company": COMPANY, "purpose": "Material Issue", "docstatus": 1},
        pluck="name", limit_page_length=10000)
    if not entries:
        return []
    details = frappe.get_all("Stock Entry Detail", filters={
        "parent": ["in", entries], "material_request": ["in", mr_names],
        "s_warehouse": WAREHOUSE},
        fields=["name", "parent", "item_code", "qty", "uom", "material_request", "material_request_item"],
        limit_page_length=10000)
    output = []
    for row in details:
        # Stock Ledger Entries are the authoritative consumption valuation.
        sle = frappe.get_all("Stock Ledger Entry", filters={
            "voucher_type": "Stock Entry", "voucher_no": row.parent,
            "voucher_detail_no": row.name, "warehouse": WAREHOUSE,
            "is_cancelled": 0},
            fields=["actual_qty", "stock_value_difference"],
            limit_page_length=100)
        negative = [x for x in sle if flt(x.actual_qty) < 0]
        cost = -sum(flt(x.stock_value_difference) for x in negative) if negative else None
        output.append({
            "detail": row.name, "stock_entry": row.parent,
            "item_code": row.item_code, "qty": flt(row.qty), "uom": row.uom,
            "material_request": row.material_request,
            "stock_cost": cost,
        })
    return output


def get_selling_rate(item_code):
    price_list = "Standard Selling"
    if not frappe.db.exists("Price List", price_list):
        return None
    prices = frappe.get_all("Item Price", filters={
        "item_code": item_code, "price_list": price_list,
        "selling": 1, "currency": "BDT"},
        fields=["price_list_rate"], order_by="modified desc", limit_page_length=1)
    return flt(prices[0].price_list_rate) if prices else None


def existing_invoices(job_name):
    return frappe.get_all("Sales Invoice", filters={
        FIELD: job_name, "company": COMPANY,
        "docstatus": ["!=", 2], "is_return": 0},
        fields=["name", "docstatus", "grand_total", "outstanding_amount"],
        limit_page_length=100)


@frappe.whitelist()
def preview_repair_bill(job_name):
    require_manager()
    job = get_job(job_name)
    issued = get_issued_rows(job_name)
    lines = {}
    for row in issued:
        code = row["item_code"]
        if code not in lines:
            lines[code] = {"item_code": code, "qty": 0, "selling_rate": get_selling_rate(code)}
        lines[code]["qty"] += row["qty"]
    return {
        "service_job": job.name, "customer": job.customer,
        "status": job.status, "parts": list(lines.values()),
        "issued_details": issued, "labor_item": LABOR_ITEM,
        "existing_invoices": existing_invoices(job_name),
        "note": "Parts come only from submitted Material Issue rows. Missing selling rates must be supplied explicitly.",
    }


@frappe.whitelist(methods=["POST"])
def create_draft_repair_invoice(job_name, labor_rate=0, part_rates=None):
    """Create Draft Sales Invoice only. No stock movement or GL postings."""
    require_manager()
    if not frappe.has_permission("Sales Invoice", "create"):
        frappe.throw("Sales Invoice create permission required", frappe.PermissionError)
    job = get_job(job_name)
    if existing_invoices(job_name):
        frappe.throw("A non-cancelled Sales Invoice already exists for this Service Job")
    if job.status not in ("Completed", "Ready to Deliver", "Delivered"):
        frappe.throw("Complete the repair before preparing the invoice")
    if isinstance(part_rates, str):
        part_rates = frappe.parse_json(part_rates)
    if part_rates is None:
        part_rates = {}
    if not isinstance(part_rates, dict):
        frappe.throw("part_rates must be a mapping of Item Code to selling rate")

    issued = get_issued_rows(job_name)
    quantities = {}
    for row in issued:
        quantities[row["item_code"]] = quantities.get(row["item_code"], 0) + row["qty"]

    rows = []
    for code, qty in quantities.items():
        item = frappe.get_doc("Item", code)
        if not item.is_sales_item or item.disabled:
            frappe.throw("Issued part is not a valid sales Item: " + code)
        reference_rate = get_selling_rate(code)
        supplied = code in part_rates
        if not supplied and reference_rate is None:
            frappe.throw("No selling price for " + code + "; provide part_rates")
        rate = finite_nonnegative(part_rates[code] if supplied else reference_rate, "Rate for " + code)
        rows.append({"item_code": code, "qty": qty, "rate": rate,
                     "warehouse": WAREHOUSE, "income_account": "Sales - AMCL"})

    labor = finite_nonnegative(labor_rate, "Labor charge")
    if labor:
        if not frappe.db.exists("Item", LABOR_ITEM):
            frappe.throw("Repair labor Item missing")
        labor_doc = frappe.get_doc("Item", LABOR_ITEM)
        if labor_doc.is_stock_item or not labor_doc.is_sales_item or labor_doc.disabled:
            frappe.throw("Repair labor Item is not configured correctly")
        rows.append({"item_code": LABOR_ITEM, "qty": 1, "rate": labor,
                     "income_account": "Service - AMCL"})
    if not rows:
        frappe.throw("No issued parts and no labor charge; cannot make empty invoice")

    invoice = frappe.get_doc({
        "doctype": "Sales Invoice", "company": COMPANY, "customer": job.customer,
        "update_stock": 0, "custom_service_job": job.name,
        "remarks": "Repair service: " + job.name + " (stock previously issued via Material Issue)",
        "items": rows,
    })
    invoice.insert()  # respects ERPNext permission and validation
    if invoice.docstatus != 0 or invoice.update_stock:
        frappe.throw("Safety assertion failed: invoice must be Draft without Update Stock")
    return {"success": True, "sales_invoice": invoice.name,
            "service_job": job.name, "docstatus": invoice.docstatus,
            "update_stock": 0, "stock_posted": False, "ledger_posted": False}


@frappe.whitelist()
def repair_contribution_report(limit=100):
    """Operational contribution: invoiced net revenue less issued stock cost.

    Internal technician labor cost and overhead are NOT included. This is
    not a complete net-profit or accounting P&L report.
    """
    require_manager()
    limit = max(1, min(int(limit), 200))
    jobs = frappe.get_all("Service Job", filters={"shop": COMPANY},
                          fields=["name", "status", "customer", "technician"],
                          order_by="modified desc", limit_page_length=limit)
    result = []
    for job in jobs:
        issued = get_issued_rows(job.name)
        costs_known = all(x["stock_cost"] is not None for x in issued)
        parts_cost = sum(x["stock_cost"] for x in issued) if costs_known else None
        invoices = existing_invoices(job.name)
        submitted = [x for x in invoices if x.docstatus == 1]
        net_sales = 0.0
        labor_sales = 0.0
        parts_sales = 0.0
        for inv in submitted:
            items = frappe.get_all("Sales Invoice Item", filters={"parent": inv.name},
                                   fields=["item_code", "base_net_amount"], limit_page_length=1000)
            for item in items:
                value = flt(item.base_net_amount)
                net_sales += value
                if item.item_code == LABOR_ITEM:
                    labor_sales += value
                else:
                    parts_sales += value
        result.append({
            "service_job": job.name, "status": job.status,
            "technician": job.technician,
            "submitted_invoices": [x.name for x in submitted],
            "net_revenue_ex_tax": net_sales if submitted else None,
            "parts_revenue_ex_tax": parts_sales if submitted else None,
            "labor_revenue_ex_tax": labor_sales if submitted else None,
            "issued_parts_cost": parts_cost,
            "contribution_before_labor_and_overhead":
                round(net_sales - parts_cost, 2) if submitted and costs_known else None,
            "cost_complete": costs_known,
        })
    return {"company": COMPANY, "currency": "BDT", "jobs": result,
            "disclaimer": "Contribution excludes internal labor, overhead, taxes, and unrelated costs; missing valuation shows null."}


def install():
    """Run using bench execute to create a single custom Sales Invoice Link field."""
    company = frappe.get_doc("Company", COMPANY)
    if company.default_currency != "BDT":
        frappe.throw("Expected BDT company")
    for account, root in (("Sales - AMCL", "Income"), ("Service - AMCL", "Income")):
        acc = frappe.get_doc("Account", account)
        if acc.company != COMPANY or acc.root_type != root or acc.is_group:
            frappe.throw("Invalid income account: " + account)
    field = frappe.get_meta("Sales Invoice").get_field(FIELD)
    if field:
        if field.fieldtype != "Link" or field.options != "Service Job":
            frappe.throw("Incompatible Sales Invoice custom_service_job field")
        return {"success": True, "custom_field": "already_exists"}
    frappe.get_doc({"doctype": "Custom Field", "dt": "Sales Invoice",
                    "fieldname": FIELD, "label": "Service Job", "fieldtype": "Link",
                    "options": "Service Job", "insert_after": "customer",
                    "in_standard_filter": 1, "no_copy": 1}).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="Sales Invoice")
    return {"success": True, "custom_field": "created",
            "invoice_created": False, "stock_posted": False}
