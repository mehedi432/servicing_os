"""SERVICING OS V7.12: atomic invoice + delivery, no duplicate stock postings."""
import frappe
from servicing_os.api.site_company_706 import validate_job_shop
from servicing_os.api.service_invoice_661 import get_job_context
from servicing_os.api.invoice_final_709 import finalize_service_invoice
from servicing_os.api.service_handover_710 import deliver_service_job


def _job(name, *, for_update=False):
    name = str(name or '').strip()
    if not name or len(name) > 140:
        frappe.throw('Select a valid Service Job.')
    if frappe.session.user == 'Guest':
        frappe.throw('Sign in before accessing repair delivery.', frappe.PermissionError)
    if for_update:
        frappe.db.sql('SELECT name FROM `tabService Job` WHERE name=%s FOR UPDATE', (name,))
    job = frappe.get_doc('Service Job', name)
    job.check_permission('read')
    validate_job_shop(job)
    return job


@frappe.whitelist(methods=['GET'])
def handover_context(job_name):
    job = _job(job_name)
    info = get_job_context(job.name)
    active = [x for x in info.get('invoices', []) if x['doctype'] == 'Sales Invoice' and x['docstatus'] != 2 and not x.get('is_return')]
    if len(active) > 1:
        issue = 'Multiple active invoices are linked to this job. Resolve duplicates before delivery.'
    elif job.status not in ('Ready to Deliver', 'Delivered'):
        issue = 'Set Service Steps to Ready to Deliver before final billing.'
    else:
        issue = ''
    return {'service_job': job.name, 'status': job.status, 'customer': info.get('customer'),
            'customer_name': info.get('customer_name'), 'invoice': active[0] if len(active) == 1 else None,
            'invoice_count': len(active), 'issue': issue,
            'can_write': bool(frappe.has_permission('Service Job', 'write', doc=job)),
            'already_delivered': job.status == 'Delivered'}


@frappe.whitelist(methods=['POST'])
def finalize_and_deliver(job_name, invoice_name, confirmation):
    """One request / one DB transaction: issue approved parts, submit invoice, handover.

    Frappe rolls back all of these changes if any step raises. No payment posting.
    """
    if str(confirmation or '').strip() != str(job_name or '').strip():
        frappe.throw('Confirm the exact Service Job before finalizing.')
    job = _job(job_name, for_update=True)
    job.check_permission('write')
    if job.status not in ('Ready to Deliver', 'Delivered'):
        frappe.throw('Service Job must be Ready to Deliver before final invoice and handover.')
    result = finalize_service_invoice(job.name, invoice_name)
    delivery = deliver_service_job(job.name, job.name)
    return {'service_job': job.name, 'invoice': result['invoice'], 'docstatus': 1,
            'status': 'Delivered', 'stock_entries': result.get('stock_entries', []),
            'already_final': result.get('already_final', False), 'already_delivered': delivery.get('already_delivered', False)}


@frappe.whitelist(methods=['POST'])
def deliver_with_existing_invoice(job_name, confirmation):
    job = _job(job_name, for_update=True)
    job.check_permission('write')
    if job.status not in ('Ready to Deliver', 'Delivered'):
        frappe.throw('Set the repair status to Ready to Deliver before handover.')
    delivery = deliver_service_job(job.name, confirmation)
    return {'service_job':job.name, 'invoice':delivery.get('invoice'),
            'docstatus':1, 'status':'Delivered', 'already_delivered':delivery.get('already_delivered', False)}
