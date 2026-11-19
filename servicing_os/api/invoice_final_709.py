"""SERVICING OS v7.09: atomic, idempotent final billing for a Service Job.

Only approved Material Requests are auto-issued. ERPNext native Stock Entry posts
parts; Sales Invoice is submitted with update_stock=0 to avoid a second issue.
No payment entries or delivery transitions are fabricated.
"""

import frappe
from frappe.utils import flt
from servicing_os.api.site_company_706 import site_shop_context, validate_job_shop


def _require():
    if frappe.session.user == 'Guest':
        frappe.throw('Login required', frappe.PermissionError)
    roles = set(frappe.get_roles())
    if frappe.session.user != 'Administrator' and not roles.intersection({'System Manager', 'Stock Manager', 'Accounts Manager'}):
        frappe.throw('A manager is required to finalize a repair invoice', frappe.PermissionError)
    for dt, action in (('Sales Invoice', 'read'), ('Sales Invoice', 'submit'), ('Stock Entry', 'create'), ('Stock Entry', 'submit')):
        if not frappe.has_permission(dt, action):
            frappe.throw(f'{action.title()} permission required for {dt}', frappe.PermissionError)


def _job_context(job_name):
    if not job_name or len(str(job_name)) > 140:
        frappe.throw('Choose a valid Service Job')
    frappe.db.sql('SELECT name FROM `tabService Job` WHERE name=%s FOR UPDATE', (job_name,))
    job = frappe.get_doc('Service Job', job_name)
    job.check_permission('read')
    validate_job_shop(job)
    if job.status not in ('Completed', 'Ready to Deliver', 'Delivered'):
        frappe.throw('Complete the repair before finalizing the invoice')
    ctx = site_shop_context()
    if job.shop != ctx['shop'] or not job.customer:
        frappe.throw('Service Job shop or customer mismatch', frappe.PermissionError)
    shop = frappe.get_doc('Servicing Shop', ctx['shop'])
    warehouse = shop.spare_parts_warehouse
    if not warehouse:
        frappe.throw('Spare Parts warehouse is missing in Servicing Shop')
    return job, ctx, warehouse


def _invoice_check(inv, job, ctx):
    if inv.company != ctx['company'] or inv.customer != job.customer or inv.get('custom_service_job') != job.name:
        frappe.throw('Invoice company/customer/Service Job mismatch', frappe.PermissionError)
    if inv.is_return or inv.update_stock:
        frappe.throw('Service Invoice must not be a return or update stock. Spare parts are issued separately.')
    if inv.docstatus == 2:
        frappe.throw('Cancelled invoice cannot be finalized')
    inv.check_permission('read')
    if not inv.items:
        frappe.throw('Invoice has no item rows')


def _requests(job, ctx, warehouse):
    if not frappe.db.has_column('Material Request', 'custom_service_job'):
        frappe.throw('Missing Material Request Service Job link; install v7.05 migration')
    names = frappe.get_all('Material Request', filters={'company':ctx['company'], 'material_request_type':'Material Issue',
                     'custom_service_job':job.name, 'docstatus':['!=',2]}, pluck='name',
                     order_by='name asc', limit_page_length=5000)
    result=[]
    for name in names:
        mr=frappe.get_doc('Material Request', name)
        if mr.docstatus not in (0,1) or mr.set_warehouse != warehouse or any(x.warehouse != warehouse for x in mr.items):
            frappe.throw('Unexpected Material Request configuration: '+name)
        result.append(mr)
    return result


def _collect_issued(job_name, company, warehouse):
    """Count stock issues solely from submitted, job-linked material requests."""
    rows = frappe.db.sql("""
      SELECT d.item_code, SUM(d.transfer_qty) AS stock_qty
      FROM `tabStock Entry Detail` d
      JOIN `tabStock Entry` se ON se.name=d.parent
      JOIN `tabMaterial Request` mr ON mr.name=d.material_request
      WHERE mr.custom_service_job=%s AND mr.company=%s AND mr.docstatus=1
        AND mr.material_request_type='Material Issue'
        AND se.company=%s AND se.docstatus=1 AND se.purpose='Material Issue'
        AND d.s_warehouse=%s AND IFNULL(d.t_warehouse,'')=''
      GROUP BY d.item_code
    """, (job_name, company, company, warehouse), as_dict=True)
    return {r.item_code:flt(r.stock_qty) for r in rows}



def _billing_check(inv, job_name, company, warehouse):
    # Every stock item billed must have been issued via a linked submitted Material Issue.
    issued = _collect_issued(job_name, company, warehouse)
    billed = {}
    for line in inv.items:
        if frappe.db.get_value('Item', line.item_code, 'is_stock_item'):
            billed[line.item_code] = billed.get(line.item_code,0) + flt(line.stock_qty or line.qty * (line.conversion_factor or 1))
    for code, qty in billed.items():
        if abs(qty - issued.get(code,0)) > 0.00001:
            frappe.throw(f'Billed part {code}: {qty} stock units; issued: {issued.get(code, 0)}. Review part requests or invoice lines before finalizing.')
    for code, qty in issued.items():
        if abs(qty - billed.get(code,0)) > 0.00001:
            frappe.throw(f'Issued part {code}: {qty} stock units; billed: {billed.get(code, 0)}. Review invoice lines before finalizing.')


@frappe.whitelist(methods=['POST'])
def finalize_service_invoice(job_name, invoice_name):
    """Submit existing Sales Invoice and approved parts issues in one Frappe request.

    Any exception before request commit rolls back invoice + stock submissions.
    Does not auto-approve draft Material Requests or create payment entries.
    """
    _require()
    job, ctx, warehouse = _job_context(str(job_name or '').strip())
    if not invoice_name or len(str(invoice_name)) > 140:
        frappe.throw('Choose a valid Sales Invoice')
    # The Service Job is already locked. Lock the existing invoice before submitting it.
    frappe.db.sql('SELECT name FROM `tabSales Invoice` WHERE name=%s FOR UPDATE', (invoice_name,))
    inv=frappe.get_doc('Sales Invoice', invoice_name)
    _invoice_check(inv, job, ctx)
    competitors=frappe.get_all('Sales Invoice', filters={'company':ctx['company'], 'custom_service_job':job.name,
                           'is_return':0,'docstatus':['!=',2]}, pluck='name', limit_page_length=100)
    if len(competitors)!=1 or competitors[0]!=inv.name:
        frappe.throw('Multiple invoices are linked to this Service Job. Resolve before finalization.')
    if inv.docstatus == 1:
        return {'invoice':inv.name,'service_job':job.name,'docstatus':1,'already_final':True,'stock_entries':[]}
    if inv.docstatus != 0:
        frappe.throw('Only Draft Sales Invoices can be finalized')
    if job.status == 'Delivered':
        frappe.throw('This device was already delivered. Review the existing Sales Invoice in ERPNext.')

    from servicing_os.api import parts_workbench_708 as parts
    requests=_requests(job, ctx, warehouse)
    # Never silently approve parts requests. Manager must approve first.
    for mr in requests:
        if mr.docstatus == 0:
            frappe.throw('Approve Draft Material Request '+mr.name+' before finalizing the invoice')
    submitted_entries=[]
    for mr in requests:
        # Use the same request lock as the standalone parts issue workflow.
        frappe.db.sql('SELECT name FROM `tabMaterial Request` WHERE name=%s FOR UPDATE', (mr.name,))
        links=parts._stock_links(mr.name, for_update=True)
        if len(links)>1:
            frappe.throw('Multiple active Stock Entries found for '+mr.name+'. Review them in Stock Entry / Issue Parts.')
        if links:
            if links[0].docstatus == 1:
                continue
            stock_entry = links[0].name
        else:
            expense, cost_center = parts.issue_accounting_defaults(ctx['company'])
            if not expense or not cost_center:
                frappe.throw('Set an active expense account and Default Cost Center on the Company, or issue the parts from Spare Parts Required before finalizing this invoice.')
            draft = parts.create_draft_stock_entry(mr.name, expense, cost_center, 'Issued during final invoice '+inv.name)
            stock_entry = draft['stock_entry']
        # The same validation applies to existing and newly mapped draft entries.
        entry = parts.submit_stock_entry(stock_entry, stock_entry)
        submitted_entries.append(entry['stock_entry'])
    _billing_check(inv,job.name,ctx['company'],warehouse)
    inv.flags.ignore_permissions=False
    inv.submit()
    return {'invoice':inv.name,'service_job':job.name,'docstatus':inv.docstatus,
            'already_final':False,'stock_entries':submitted_entries}


def verify():
    return {'module':'invoice_final_709','site':site_shop_context(),
            'sales_invoice_link':bool(frappe.db.has_column('Sales Invoice','custom_service_job')),
            'material_request_link':bool(frappe.db.has_column('Material Request','custom_service_job'))}


def install():
    """Idempotent schema checks for new and existing Frappe sites."""
    from servicing_os.parts_request_schema_705 import ensure, ensure_service_job_link

    fields = [ensure_service_job_link("Sales Invoice", "customer"), ensure()]
    added = [f"{field['doctype']}.{field['field']}" for field in fields if field["action"] == "created"]
    return {"created": added, "verified": verify()}
