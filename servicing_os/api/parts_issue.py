import frappe
from frappe.utils import flt

from servicing_os.api.site_company_706 import current_company, validate_job_shop
WAREHOUSE = "Spare Parts - AMCL"
MANAGERS = {"System Manager", "Stock Manager"}


def _authorize(write=False):
    user = frappe.session.user
    if user != "Administrator" and not MANAGERS.intersection(set(frappe.get_roles(user))):
        frappe.throw("Stock Manager or System Manager role required.", frappe.PermissionError)
    if write and not frappe.has_permission("Stock Entry", "create"):
        frappe.throw("Stock Entry create permission required.", frappe.PermissionError)
    if not frappe.has_permission("Material Request", "read"):
        frappe.throw("Material Request read permission required.", frappe.PermissionError)


def _get_mr(name):
    mr=frappe.get_doc("Material Request", name)
    mr.check_permission("read")
    if mr.company != current_company() or mr.material_request_type != "Material Issue":
        frappe.throw("Material Request company or purpose mismatch.")
    if mr.docstatus != 1 or mr.status in ("Stopped", "Cancelled"):
        frappe.throw("Only active, submitted Material Issue requests can be issued.")
    if not mr.get("custom_service_job"):
        frappe.throw("Material Request is not linked to a Service Job.")
    job=frappe.get_doc("Service Job", mr.custom_service_job)
    if job.status in ("Cancelled", "Delivered"):
        frappe.throw("Cannot issue parts for a closed Service Job.")
    validate_job_shop(job)
    return mr


def _issued_map(name):
    # Standard ERPNext Stock Entry Detail links preserve request-item identity.
    rows=frappe.db.sql("""
        SELECT sed.material_request_item, SUM(sed.transfer_qty) AS qty
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON se.name=sed.parent
        WHERE sed.material_request=%s AND sed.docstatus=1
          AND se.docstatus=1 AND se.purpose='Material Issue'
          AND sed.s_warehouse=%s
        GROUP BY sed.material_request_item
    """, (name, WAREHOUSE), as_dict=True)
    return {x.material_request_item: flt(x.qty) for x in rows}


def _drafts(name):
    rows=frappe.db.sql("""
        SELECT DISTINCT se.name
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent=se.name
        WHERE se.docstatus=0 AND se.purpose='Material Issue'
          AND sed.material_request=%s
        ORDER BY se.name
    """, (name,), as_dict=True)
    return [x.name for x in rows]


def _get_lines(mr):
    issued=_issued_map(mr.name)
    lines=[]
    for r in mr.items:
        if r.warehouse != WAREHOUSE:
            frappe.throw("Material Request row has an unexpected warehouse: " + r.item_code)
        item=frappe.db.get_value("Item", r.item_code,
            ["is_stock_item", "is_sales_item", "disabled", "stock_uom"], as_dict=True)
        if not item or item.disabled or not item.is_stock_item or not item.is_sales_item:
            frappe.throw("Item is not an active sales-enabled stock Item: " + r.item_code)
        if not flt(r.conversion_factor or 1):
            frappe.throw("Invalid UOM conversion for " + r.item_code)
        requested=flt(r.stock_qty or (flt(r.qty)*flt(r.conversion_factor or 1)), 6)
        remaining=max(0,flt(requested - issued.get(r.name, 0), 6))
        stock=frappe.db.get_value("Bin", {"warehouse":WAREHOUSE,"item_code":r.item_code},
            ["actual_qty","reserved_qty"], as_dict=True)
        actual=flt(stock.actual_qty) if stock else 0
        lines.append({"row_name":r.name,"item_code":r.item_code,"item_name":r.item_name,
            "uom":item.stock_uom,"requested_qty":requested,"already_issued_qty":issued.get(r.name,0),
            "remaining_qty":remaining,"actual_qty":actual})
    return lines


@frappe.whitelist()
def get_issue_candidates():
    _authorize()
    mrs=frappe.get_list("Material Request", filters={
        "company":current_company(),"material_request_type":"Material Issue",
        "docstatus":1,"custom_service_job":["is","set"]},
        fields=["name","custom_service_job","status","transaction_date"],
        order_by="modified desc", limit_page_length=100)
    entries=[]
    for x in mrs:
        if x.status in ("Stopped", "Cancelled"):
            continue
        try:
            mr=_get_mr(x.name)
            lines=_get_lines(mr)
            if not any(r["remaining_qty"]>0 for r in lines):
                continue
            entries.append({"name":mr.name,"service_job":mr.custom_service_job,
                "status":mr.status,"lines":lines,"drafts":_drafts(mr.name)})
        except frappe.PermissionError:
            continue
    return {"requests":entries,"warehouse":WAREHOUSE,"company":current_company(),
        "can_create": bool(frappe.has_permission("Stock Entry", "create"))}


@frappe.whitelist(methods=["POST"])
def create_draft_issue(material_request):
    """Create exactly one draft for all currently unissued request quantities.

    Review and submit in ERPNext Desk. Never submits or posts stock here.
    """
    _authorize(write=True)
    mr=_get_mr(material_request)
    existing=_drafts(mr.name)
    if existing:
        frappe.throw("Existing draft Stock Entry " + existing[0] + " must be reviewed first.")
    lines=_get_lines(mr)
    to_issue=[r for r in lines if r["remaining_qty"]>0]
    if not to_issue:
        frappe.throw("This Material Request has no unissued quantities.")
    if len(to_issue)>100:
        frappe.throw("Maximum 100 lines per issue.")
    # ERPNext may have reservations beyond actual stock. Stock posting still
    # uses native ledger checks at submit-time; this is only a draft precheck.
    requested_totals={}
    for r in to_issue:
        requested_totals[r["item_code"]]=requested_totals.get(r["item_code"],0)+r["remaining_qty"]
    for code, qty in requested_totals.items():
        available=frappe.db.get_value("Bin",{"item_code":code,"warehouse":WAREHOUSE},"actual_qty") or 0
        if flt(available)+1e-7 < qty:
            frappe.throw("Insufficient on-hand stock for " + code + ". Available " + str(available) + ", needed " + str(qty))
    company=frappe.get_doc("Company", current_company())
    cost_center=company.default_cost_center
    expense_account=company.default_expense_account
    if not expense_account or not frappe.db.exists("Account",expense_account):
        frappe.throw("Configure Company default expense account before issuing parts.")
    wh=frappe.get_doc("Warehouse",WAREHOUSE)
    if wh.company!=current_company() or wh.is_group or wh.disabled:
        frappe.throw("Spare Parts warehouse is unavailable.")
    entry=frappe.get_doc({"doctype":"Stock Entry","stock_entry_type":"Material Issue",
        "purpose":"Material Issue","company":current_company(),
        "from_warehouse":WAREHOUSE,
        "remarks":"Repair parts for " + mr.custom_service_job + " / Material Request " + mr.name,
        "items":[{
            "item_code":r["item_code"],"qty":r["remaining_qty"],"uom":r["uom"],
            "stock_uom":r["uom"],"conversion_factor":1,"s_warehouse":WAREHOUSE,
            "material_request":mr.name,"material_request_item":r["row_name"],
            "expense_account":expense_account,"cost_center":cost_center,
        } for r in to_issue]})
    # Keep native Stock Entry validations and permissions; only draft is inserted.
    entry.insert()
    return {"success":True,"stock_entry":entry.name,"service_job":mr.custom_service_job,
        "material_request":mr.name,"docstatus":entry.docstatus,"stock_posted":False,
        "item_lines":len(to_issue)}
