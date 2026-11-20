"""SERVICING OS V7.08 — Repair parts: draft requests + controlled stock issue.

No schema changes; Material Request.custom_service_job is provided by V7.05.
Stock changes ONLY occur on an explicitly confirmed Stock Entry submit.
"""
import json
from decimal import Decimal, InvalidOperation

import frappe
from frappe.utils import flt, nowdate
from servicing_os.api.site_company_706 import site_shop_context, validate_job_shop

MANAGERS = {"System Manager", "Stock Manager"}


def _manager():
    user = frappe.session.user
    return user == "Administrator" or bool(MANAGERS.intersection(set(frappe.get_roles(user))))


def _job(job_name, write=False):
    if frappe.session.user == "Guest":
        frappe.throw("Login required", frappe.PermissionError)
    from servicing_os.api.parts_request import check_job_access
    job = check_job_access(str(job_name or "").strip(), write=write)
    validate_job_shop(job)
    if write and job.status in ("Delivered", "Cancelled", "Canceled"):
        frappe.throw("This Service Job is closed")
    return job


def _scope(job_name):
    job = _job(job_name)
    context = site_shop_context()
    shop = frappe.get_doc("Servicing Shop", context["shop"])
    warehouse = str(shop.get("spare_parts_warehouse") or "").strip()
    if not warehouse:
        frappe.throw("Configure the Spare Parts Warehouse on Servicing Shop")
    wh = frappe.get_doc("Warehouse", warehouse)
    if wh.company != context["company"] or wh.disabled or wh.is_group:
        frappe.throw("Invalid active Spare Parts Warehouse")
    return job, context, warehouse


def _mr(name):
    if not name or len(str(name)) > 140:
        frappe.throw("Material Request is required")
    doc = frappe.get_doc("Material Request", name)
    if not doc.get("custom_service_job") or doc.material_request_type != "Material Issue":
        frappe.throw("Not a repair-parts Material Request", frappe.PermissionError)
    job, context, warehouse = _scope(doc.custom_service_job)
    if doc.company != context["company"] or doc.set_warehouse != warehouse:
        frappe.throw("Material Request belongs to another shop/company or warehouse", frappe.PermissionError)
    if any(r.warehouse != warehouse for r in doc.items):
        frappe.throw("Material Request contains an unexpected warehouse")
    return doc, warehouse, context


def _stock_links(name, *, for_update=False):
    lock = " FOR UPDATE" if for_update else ""
    return frappe.db.sql("""
        SELECT se.name, se.docstatus
        FROM `tabStock Entry` se
        WHERE se.docstatus IN (0, 1) AND EXISTS (
            SELECT 1 FROM `tabStock Entry Detail` d
            WHERE d.parent=se.name AND d.material_request=%s
        )
        ORDER BY se.creation DESC LIMIT 20
    """ + lock, (name,), as_dict=True)


def _manager_require(create=False, submit=False):
    if not _manager():
        frappe.throw("Stock Manager or System Manager required", frappe.PermissionError)
    if create and not frappe.has_permission("Stock Entry", "create"):
        frappe.throw("Stock Entry create permission required", frappe.PermissionError)
    if submit and not frappe.has_permission("Stock Entry", "submit"):
        frappe.throw("Stock Entry submit permission required", frappe.PermissionError)


def _positive_qty(value):
    try:
        v = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        frappe.throw("Enter a valid quantity")
    if not v.is_finite() or v <= 0 or v > 100000:
        frappe.throw("Quantity must be between 0 and 100000")
    return float(v)


def _active_account(name, company):
    return name and frappe.db.exists("Account", {
        "name": name, "company": company, "is_group": 0, "disabled": 0, "root_type": "Expense",
    })


def _active_cost_center(name, company):
    return name and frappe.db.exists("Cost Center", {
        "name": name, "company": company, "is_group": 0, "disabled": 0,
    })


def issue_accounting_defaults(company_name):
    company = frappe.get_doc("Company", company_name)
    expense_account = next((name for name in (
        company.get("default_expense_account"), company.get("stock_adjustment_account"),
    ) if _active_account(name, company_name)), "")
    cost_center = next((name for name in (
        company.get("cost_center"), company.get("default_cost_center"),
    ) if _active_cost_center(name, company_name)), "")
    return expense_account, cost_center


def _account(name, company):
    if not _active_account(name, company):
        frappe.throw("Select an active expense account from this company")


def _cost_center(name, company):
    if not _active_cost_center(name, company):
        frappe.throw("Select an active cost center from this company")


def _stock_balance(row):
    on_hand = flt(row.actual_qty, 6) if row else 0
    reserved = max(0, flt(row.reserved_qty, 6)) if row else 0
    return {"on_hand": on_hand, "reserved": reserved, "available": max(0, flt(on_hand - reserved, 6))}


def _warehouse_balances(item_codes, company, source):
    if not item_codes or not frappe.has_permission("Warehouse", "read"):
        return {}
    warehouses = frappe.get_list("Warehouse", filters={
        "company": company, "disabled": 0, "is_group": 0, "name": ["!=", source],
    }, pluck="name", limit_page_length=0)
    if not warehouses:
        return {}
    bins = frappe.get_all("Bin", filters={"warehouse": ["in", warehouses], "item_code": ["in", item_codes], "actual_qty": [">", 0]},
                          fields=["item_code", "warehouse", "actual_qty", "reserved_qty"], order_by="warehouse asc")
    balances = {}
    for row in bins:
        available = _stock_balance(row)["available"]
        if available:
            balances.setdefault(row.item_code, []).append({"warehouse": row.warehouse, "available": available})
    return balances


@frappe.whitelist(methods=["GET"])
def overview(job_name):
    job, context, warehouse = _scope(job_name)
    if not frappe.db.has_column("Material Request", "custom_service_job"):
        frappe.throw("Missing Material Request.custom_service_job: run bench migrate")
    requests = frappe.get_all(
        "Material Request",
        filters={"custom_service_job":job.name, "material_request_type":"Material Issue", "company":context["company"]},
        fields=["name", "status", "docstatus", "transaction_date", "owner", "modified"],
        order_by="creation desc", limit_page_length=100,
    )
    for r in requests:
        mr = frappe.get_doc("Material Request", r.name)
        r["items"] = [
            {"name": x.name, "item_code": x.item_code, "item_name": x.item_name, "qty": x.qty,
             "uom": x.uom, "stock_qty": flt(x.stock_qty or x.qty * flt(x.conversion_factor or 1))}
            for x in mr.items
        ]
        r["stock_entries"] = [{"name":x.name, "docstatus":x.docstatus} for x in _stock_links(r.name)]
    manager = _manager()
    return {
        "job":job.name, "job_status":job.status,
        "company":context["company"], "warehouse": warehouse,
        "requests":requests, "manager":manager,
        "can_stock_create":bool(manager and frappe.has_permission("Stock Entry","create")),
        "can_stock_submit":bool(manager and frappe.has_permission("Stock Entry","submit")),
        "can_approve":bool(manager),
    }


@frappe.whitelist(methods=["GET"])
def search_items(job_name, search=""):
    _, _, warehouse = _scope(job_name)
    term = str(search or "").strip()[:80]
    if not frappe.has_permission("Item", "read"):
        frappe.throw("You do not have permission to read stock items.", frappe.PermissionError)
    query = {}
    if term:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        query["or_filters"] = [["name", "like", pattern], ["item_name", "like", pattern]]
    rows = frappe.get_list(
        "Item", filters={"disabled": 0, "is_stock_item": 1},
        fields=["name", "item_name", "stock_uom"], order_by="item_name asc, name asc",
        limit_page_length=8, **query,
    )
    if not rows:
        return {"items":[]}
    bins = frappe.get_all("Bin", filters={"warehouse":warehouse,"item_code":["in",[x.name for x in rows]]},
                          fields=["item_code", "actual_qty", "reserved_qty"])
    stock={b.item_code:_stock_balance(b)["available"] for b in bins}
    return {"warehouse":warehouse,"items":[{"item_code":x.name,"item_name":x.item_name,"uom":x.stock_uom,
                      "available_qty":stock.get(x.name,0)} for x in rows]}


@frappe.whitelist(methods=["POST"])
def create_request(job_name, items, remarks=""):
    job = _job(job_name, write=True)
    _, context, warehouse = _scope(job.name)
    if isinstance(items, str):
        items = json.loads(items)
    if not isinstance(items, list) or not (1 <= len(items) <= 100):
        frappe.throw("Choose between 1 and 100 parts")
    if not frappe.db.has_column("Material Request", "custom_service_job"):
        frappe.throw("Material Request Service Job field is missing. Run bench migrate")
    lines=[]
    seen=set()
    for i, line in enumerate(items,1):
        if not isinstance(line,dict):
            frappe.throw("Invalid row %s" % i)
        code=str(line.get("item_code") or "").strip()
        if not code or code in seen:
            frappe.throw("Select unique Item Codes for every row")
        seen.add(code)
        data=frappe.db.get_value("Item", code, ["disabled","is_stock_item","stock_uom"], as_dict=True)
        if not data or data.disabled or not data.is_stock_item:
            frappe.throw("Invalid stock part: " + code)
        lines.append({"item_code":code,"qty":_positive_qty(line.get("qty")),
                     "uom":data.stock_uom,"schedule_date":nowdate(),"warehouse":warehouse})
    doc=frappe.get_doc({"doctype":"Material Request", "material_request_type":"Material Issue",
      "company":context["company"], "transaction_date":nowdate(), "schedule_date":nowdate(),
      "set_warehouse":warehouse, "custom_service_job":job.name,
      "remarks":"Repair parts for " + job.name + " | Requested by " + frappe.session.user + "\n" + str(remarks or "")[:500],
      "items":lines})
    doc.insert(ignore_permissions=True)
    return {"material_request":doc.name,"line_count":len(lines),"stock_deducted":False}


@frappe.whitelist(methods=["POST"])
def approve_request(material_request):
    _manager_require()
    doc, _, _ = _mr(material_request)
    _job(doc.custom_service_job, write=True)
    if doc.docstatus != 0:
        frappe.throw("Only Draft requests can be approved")
    doc.flags.ignore_permissions=True
    doc.submit()
    return {"material_request":doc.name,"status":"Approved","stock_deducted":False}


@frappe.whitelist(methods=["GET"])
def issue_preview(material_request):
    _manager_require()
    mr, warehouse, context = _mr(material_request)
    _job(mr.custom_service_job, write=True)
    if mr.docstatus != 1:
        frappe.throw("Approve the Material Request first")
    links=_stock_links(mr.name)
    expense_account, cost_center = issue_accounting_defaults(context["company"])
    expenses = frappe.get_all("Account", filters={"company":context["company"],"disabled":0,"is_group":0,"root_type":"Expense"},
                       fields=["name"], order_by="name asc", limit_page_length=200)
    centers=frappe.get_all("Cost Center", filters={"company":context["company"],"disabled":0,"is_group":0},
                       fields=["name"], order_by="name asc", limit_page_length=200)
    # Multiple request rows for the same item must share a single warehouse balance.
    lines = {}
    for r in mr.items:
        if r.item_code not in lines:
            item = frappe.get_doc("Item", r.item_code)
            row = frappe.db.get_value("Bin", {"item_code": r.item_code, "warehouse": warehouse},
                                      ["actual_qty", "reserved_qty"], as_dict=True)
            lines[r.item_code] = {"item_code": r.item_code, "item_name": r.item_name, "qty": 0,
                                  "uom": item.stock_uom, **_stock_balance(row),
                                  "serial_or_batch": bool(item.has_serial_no or item.has_batch_no)}
        line = lines[r.item_code]
        line["qty"] = flt(line["qty"] + flt(r.stock_qty or r.qty * flt(r.conversion_factor or 1)), 6)
    shortages = {}
    for code, line in lines.items():
        line["shortage"] = max(0, flt(line["qty"] - line["available"], 6))
        if line["shortage"] > 0.000001:
            shortages[code] = line["shortage"]
    other_balances = _warehouse_balances(list(shortages), context["company"], warehouse)
    for code in shortages:
        lines[code]["other_warehouses"] = other_balances.get(code, [])
    return {"material_request":mr.name,"service_job":mr.custom_service_job,
        "company":context["company"],"warehouse":warehouse,"posting_date":nowdate(),
        "expense_account":expense_account, "cost_center":cost_center,
        "expense_accounts":list(dict.fromkeys(name for name in [expense_account, *(x.name for x in expenses)] if name)),
        "cost_centers":list(dict.fromkeys(name for name in [cost_center, *(x.name for x in centers)] if name)),
        "stock_entries":[{"name":x.name,"docstatus":x.docstatus} for x in links],
        "items":list(lines.values()), "can_create":bool(frappe.has_permission("Stock Entry","create")),
        "can_submit":bool(frappe.has_permission("Stock Entry","submit"))}


@frappe.whitelist(methods=["POST"])
def create_draft_stock_entry(material_request, expense_account, cost_center, remarks=""):
    _manager_require(create=True)
    # Restrict two simultaneous drafts referencing the same MR.
    frappe.db.sql("SELECT name FROM `tabMaterial Request` WHERE name=%s FOR UPDATE", (material_request,))
    mr, warehouse, context = _mr(material_request)
    _job(mr.custom_service_job, write=True)
    if mr.docstatus != 1 or mr.status in ("Stopped", "Cancelled"):
        frappe.throw("Only approved, active requests can be issued")
    existing=_stock_links(mr.name, for_update=True)
    if existing:
        frappe.throw("Existing Stock Entry " + existing[0].name + ". Resolve it before creating another")
    _account(expense_account, context["company"])
    _cost_center(cost_center, context["company"])
    from erpnext.stock.doctype.material_request.material_request import make_stock_entry
    entry=make_stock_entry(mr.name)
    if not entry.items or entry.purpose != "Material Issue" or entry.company != context["company"]:
        frappe.throw("Unexpected ERPNext stock mapping. No draft created")
    for row in entry.items:
        if row.material_request != mr.name or row.s_warehouse != warehouse or row.t_warehouse:
            frappe.throw("Unexpected warehouse or Material Request mapping")
        if flt(row.qty) <= 0:
            frappe.throw("Invalid mapped stock quantity")
        row.expense_account=expense_account
        row.cost_center=cost_center
    entry.stock_entry_type="Material Issue"
    entry.remarks="Repair Job " + mr.custom_service_job + " / " + mr.name + "\n" + str(remarks or "")[:500]
    entry.insert()  # Native permissions, valuation, required fields and validations.
    return {"stock_entry":entry.name, "docstatus":0, "stock_deducted":False}


@frappe.whitelist(methods=["POST"])
def submit_stock_entry(stock_entry, confirm):
    _manager_require(submit=True)
    if not stock_entry or str(confirm or "").strip() != str(stock_entry).strip():
        frappe.throw("Type the exact Stock Entry ID to confirm the stock issue")
    se=frappe.get_doc("Stock Entry",stock_entry)
    se.check_permission("submit")
    if se.docstatus != 0 or se.purpose != "Material Issue" or not se.items:
        frappe.throw("Only Draft Material Issue Stock Entries can be submitted")
    linked={x.material_request for x in se.items}
    if len(linked)!=1 or not next(iter(linked)):
        frappe.throw("All Stock Entry rows must refer to one Material Request")
    mr_name=next(iter(linked))
    frappe.db.sql("SELECT name FROM `tabMaterial Request` WHERE name=%s FOR UPDATE", (mr_name,))
    mr, warehouse, context = _mr(mr_name)
    _job(mr.custom_service_job, write=True)
    if mr.docstatus != 1 or mr.status in ("Stopped", "Cancelled") or se.company != context["company"]:
        frappe.throw("Material Request must be approved and active in the current company")
    links=_stock_links(mr.name, for_update=True)
    if len(links)!=1 or links[0].name!=se.name or links[0].docstatus!=0:
        frappe.throw("Another active Stock Entry exists; review stock issue history")
    requested={x.name:flt(x.stock_qty or x.qty*flt(x.conversion_factor or 1)) for x in mr.items}
    mapped={}
    needed={}
    for line in se.items:
        if line.material_request != mr.name or line.s_warehouse != warehouse or line.t_warehouse:
            frappe.throw("Wrong warehouse or request mapping")
        source=next((r for r in mr.items if r.name==line.material_request_item),None)
        if not source or source.item_code!=line.item_code:
            frappe.throw("Incorrect Material Request item link")
        item=frappe.get_doc("Item",line.item_code)
        if item.has_serial_no or item.has_batch_no:
            frappe.throw("Serial/batch items must be reviewed and submitted in ERPNext Desk")
        qty=flt(line.transfer_qty or flt(line.qty)*flt(line.conversion_factor or 1),6)
        if qty<=0:frappe.throw("Invalid stock quantity")
        mapped[source.name]=mapped.get(source.name,0)+qty
        needed[line.item_code]=needed.get(line.item_code,0)+qty
    if set(mapped)!=set(requested) or any(abs(mapped[k]-v)>0.000001 for k,v in requested.items()):
        frappe.throw(f"Stock Entry {se.name} quantity differs from approved Material Request {mr.name}. Review it in ERPNext.")
    for code, amount in needed.items():
        b=frappe.db.get_value("Bin",{"warehouse":warehouse,"item_code":code},["actual_qty","reserved_qty"],as_dict=True)
        available = _stock_balance(b)["available"]
        if available+0.000001<amount:
            frappe.throw(f"Stock Entry {se.name}: {code} needs {amount:g} in {warehouse}; {available:g} available. Replenish the warehouse and retry.")
    se.submit()  # Only stock-posting action; ERPNext creates Stock Ledger Entries.
    return {"stock_entry":se.name,"docstatus":se.docstatus,"stock_deducted":se.docstatus==1,
            "service_job":mr.custom_service_job}


def verify():
    return {"module":"parts_workbench_708", "material_request_link":bool(frappe.db.has_column("Material Request","custom_service_job")),
            "site":site_shop_context(),"no_new_doctype":True}
