"""SERVICING OS 7.10: authorized, idempotent Service Job handover."""
import frappe
from servicing_os.api.site_company_706 import validate_job_shop

@frappe.whitelist(methods=['POST'])
def deliver_service_job(job_name, confirmation):
    name = str(job_name or '').strip()
    if not name or len(name)>140 or str(confirmation or '').strip()!=name:
        frappe.throw('Confirm the exact Service Job number before delivery.')
    if frappe.session.user=='Guest':
        frappe.throw('Login required',frappe.PermissionError)
    frappe.db.sql('SELECT name FROM `tabService Job` WHERE name=%s FOR UPDATE',(name,))
    job=frappe.get_doc('Service Job',name)
    job.check_permission('read')
    job.check_permission('write')
    validate_job_shop(job)
    if job.status=='Delivered':
        return {'service_job':name,'status':'Delivered','already_delivered':True}
    if job.status not in ('Completed','Ready to Deliver'):
        frappe.throw('Complete the repair before delivery.')
    if not frappe.db.has_column('Sales Invoice','custom_service_job'):
        frappe.throw('Sales Invoice Service Job link missing; run schema migration.')
    invoices=frappe.get_all('Sales Invoice',filters={
        'custom_service_job':name,'company':frappe.db.get_value('Servicing Shop',job.shop,'company'),
        'is_return':0,'docstatus':['!=',2]},fields=['name','docstatus','customer'],limit_page_length=10)
    if len(invoices)!=1 or invoices[0].docstatus!=1 or invoices[0].customer!=job.customer:
        frappe.throw('Exactly one submitted Sales Invoice for this Service Job is required before delivery.')
    job.status='Delivered'
    job.save()
    return {'service_job':name,'status':'Delivered','invoice':invoices[0].name,'already_delivered':False}


# SOS_PREMIUM_HANDOVER_711 — permission-aware, read-only prerequisites.
@frappe.whitelist(methods=['GET'])
def get_handover_readiness(job_name):
    name = str(job_name or '').strip()
    if not name or len(name)>140 or frappe.session.user=='Guest':
        frappe.throw('A valid, signed-in Service Job is required.', frappe.PermissionError)
    job = frappe.get_doc('Service Job', name)
    job.check_permission('read')
    validate_job_shop(job)
    can_write = bool(frappe.has_permission('Service Job', 'write', doc=job))
    company = frappe.db.get_value('Servicing Shop', job.shop, 'company')
    if not company:
        frappe.throw('The Servicing Shop has no ERPNext Company.')
    status = str(job.status or '')
    repair_ready = status in ('Completed', 'Ready to Deliver', 'Delivered')
    eligible = status in ('Completed', 'Ready to Deliver')
    invoice_ready = False
    invoice_name = ''
    invoice_hint = ''
    if not frappe.db.has_column('Sales Invoice', 'custom_service_job'):
        invoice_hint = 'Sales Invoice Service Job link is missing; run schema migration.'
    elif not frappe.has_permission('Sales Invoice', 'read'):
        invoice_hint = 'Invoice review requires Sales Invoice read permission.'
    else:
        invoices = frappe.get_list('Sales Invoice', filters={
            'custom_service_job': name, 'company': company, 'is_return': 0,
            'docstatus': ['!=',2]}, fields=['name','docstatus','customer'],
            limit_page_length=10)
        if len(invoices)==1:
            inv = invoices[0]
            invoice_name = inv.name
            invoice_ready = inv.docstatus == 1 and inv.customer == job.customer
            invoice_hint = 'Invoice is a draft.' if inv.docstatus == 0 else 'Invoice/customer mismatch.'
        elif len(invoices)>1:
            invoice_hint = 'Multiple active invoices found; resolve duplicates.'
        else:
            invoice_hint = 'No submitted Sales Invoice linked to this Service Job.'
    return dict(service_job=name, status=status, repair_ready=repair_ready,
                invoice_ready=invoice_ready, invoice_name=invoice_name,
                invoice_hint=invoice_hint, can_write=can_write,
                already_delivered=status=='Delivered', eligible=bool(eligible and invoice_ready and can_write))
