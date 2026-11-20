"""SERVICING OS V7.12: atomic invoice + delivery, no duplicate stock postings."""
import frappe
from frappe.utils import cint, flt
from servicing_os.api import parts_workbench_708 as parts
from servicing_os.api.site_company_706 import validate_job_shop
from servicing_os.api.service_invoice_661 import get_job_context, linked_job
from servicing_os.api.invoice_final_709 import _requests, finalize_service_invoice
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
    from servicing_os.api.invoice_payment import can_receive

    return {'service_job': job.name, 'allow_payment': can_receive(), 'status': job.status, 'customer': info.get('customer'),
            'customer_name': info.get('customer_name'), 'invoice': active[0] if len(active) == 1 else None,
            'device': {key: job.get(key) for key in ('device_type', 'brand', 'device_model', 'serial_number')},
            'invoice_count': len(active), 'issue': issue,
            'can_write': bool(frappe.has_permission('Service Job', 'write', doc=job)),
            'already_delivered': job.status == 'Delivered'}


@frappe.whitelist(methods=['GET'])
def handover_parts(job_name):
    """Read available quantities and document statuses for the selected handover."""
    job = _job(job_name)
    if not all(frappe.has_permission(doctype, 'read') for doctype in ('Material Request', 'Stock Entry')):
        return {'checked': False}

    try:
        _, context, warehouse = parts._scope(job.name)
    except frappe.PermissionError:
        return {'checked': False}
    if not frappe.has_permission('Warehouse', 'read', doc=warehouse):
        return {'checked': False}

    requests, demand = [], {}
    for request in _requests(job, context, warehouse):
        if not frappe.has_permission('Material Request', 'read', doc=request):
            return {'checked': False}
        links = parts._stock_links(request.name)
        if any(not frappe.has_permission('Stock Entry', 'read', doc=entry.name) for entry in links):
            return {'checked': False}
        if request.docstatus == 0:
            state = 'approval'
        elif len(links) > 1:
            state = 'duplicates'
        elif links and links[0].docstatus == 1:
            state = 'issued'
        elif request.status in ('Stopped', 'Cancelled'):
            state = 'stopped'
        else:
            state = 'pending'
            for item in request.items:
                if item.item_code not in demand:
                    demand[item.item_code] = {
                        'item_code': item.item_code, 'item_name': item.item_name,
                        'uom': item.stock_uom or item.uom, 'required': 0,
                    }
                demand[item.item_code]['required'] += flt(item.stock_qty or item.qty * flt(item.conversion_factor or 1))
        requests.append({
            'name': request.name,
            'state': state,
            'entries': [{'name': entry.name, 'docstatus': entry.docstatus} for entry in links],
        })

    bins = frappe.get_all('Bin', filters={'warehouse': warehouse, 'item_code': ['in', list(demand)]},
                          fields=['item_code', 'actual_qty', 'reserved_qty']) if demand else []
    balances = {row.item_code: parts._stock_balance(row)['available'] for row in bins}
    tracking = frappe.get_all('Item', filters={'name': ['in', list(demand)]},
                              fields=['name', 'has_serial_no', 'has_batch_no']) if demand else []
    needs_tracking = {row.name for row in tracking if row.has_serial_no or row.has_batch_no}
    for code, item in demand.items():
        available = balances.get(code, 0)
        item.update(available=available, required=flt(item['required'], 6),
                    shortage=max(0, flt(item['required'] - available, 6)), manual_issue=code in needs_tracking)
    return {'checked': True, 'warehouse': warehouse, 'requests': requests, 'items': list(demand.values())}


def _lock_reviewed_invoice(invoice_name, expected_modified):
    if expected_modified:
        rows = frappe.db.sql('SELECT modified FROM `tabSales Invoice` WHERE name=%s FOR UPDATE', (invoice_name,))
        if not rows or str(rows[0][0]) != str(expected_modified):
            frappe.throw('The invoice changed after review. Reload the invoice and verify the total before handover.')


@frappe.whitelist(methods=['POST'])
def finalize_and_deliver(job_name, invoice_name, confirmation, expected_modified=None):
    """One request / one DB transaction: issue approved parts, submit invoice, handover.

    Frappe rolls back all of these changes if any step raises. No payment posting.
    """
    if str(confirmation or '').strip() != str(job_name or '').strip():
        frappe.throw('Confirm the exact Service Job before finalizing.')
    job = _job(job_name, for_update=True)
    job.check_permission('write')
    if job.status not in ('Ready to Deliver', 'Delivered'):
        frappe.throw('Service Job must be Ready to Deliver before final invoice and handover.')
    if job.status != 'Delivered':
        _lock_reviewed_invoice(invoice_name, expected_modified)
    result = finalize_service_invoice(job.name, invoice_name)
    delivery = deliver_service_job(job.name, job.name)
    return {'service_job': job.name, 'invoice': result['invoice'], 'docstatus': 1,
            'status': 'Delivered', 'stock_entries': result.get('stock_entries', []),
            'already_final': result.get('already_final', False), 'already_delivered': delivery.get('already_delivered', False)}


@frappe.whitelist(methods=['POST'])
def submit_for_payment(job_name, invoice_name, expected_modified):
    """Finalize the reviewed invoice and stock issue while the device stays at the counter."""
    job = _job(job_name, for_update=True)
    job.check_permission('write')
    if job.status != 'Ready to Deliver' or not expected_modified:
        frappe.throw('Review the saved invoice for a Service Job that is Ready to Deliver.')
    return finalize_service_invoice(job.name, invoice_name, expected_modified=expected_modified)


@frappe.whitelist(methods=['POST'])
def deliver_with_existing_invoice(job_name, confirmation, invoice_name=None, expected_modified=None,
                                  expected_outstanding=None, allow_outstanding=0):
    job = _job(job_name, for_update=True)
    job.check_permission('write')
    if job.status not in ('Ready to Deliver', 'Delivered'):
        frappe.throw('Set the repair status to Ready to Deliver before handover.')
    if invoice_name:
        if job.status != 'Delivered':
            _lock_reviewed_invoice(invoice_name, expected_modified)
        invoice = frappe.get_doc('Sales Invoice', invoice_name)
        invoice.check_permission('read')
        if linked_job(invoice) != job.name or invoice.customer != job.customer or invoice.docstatus != 1:
            frappe.throw('The reviewed Sales Invoice changed. Reload the Delivery Desk and review it again.')
        if job.status != 'Delivered' and expected_outstanding is not None:
            from servicing_os.api.invoice_payment import _balance

            current = frappe.db.sql(
                'SELECT outstanding_amount FROM `tabSales Invoice` WHERE name=%s FOR UPDATE', (invoice.name,))
            due = _balance(invoice, current[0][0])
            if _balance(invoice, expected_outstanding) != due:
                frappe.throw('The balance changed. Reload the invoice before handover.')
            if due > 0 and not cint(allow_outstanding):
                frappe.throw('Record payment or explicitly confirm handover with an outstanding balance.')
    delivery = deliver_service_job(job.name, confirmation)
    return {'service_job':job.name, 'invoice':delivery.get('invoice') or invoice_name,
            'docstatus':1, 'status':'Delivered', 'already_delivered':delivery.get('already_delivered', False)}
