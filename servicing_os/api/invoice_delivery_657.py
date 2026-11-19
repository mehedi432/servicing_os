"""SERVICING OS 6.57: invoice delivery tracking and permission-checked print data.

Only a successfully submitted sale can trigger automatic handover status.
Retail stock sales need ERPNext's posted stock move (or linked Delivery Note).
No payment, invoice submission, or stock transaction is performed here.
"""
import frappe
from frappe.utils import now_datetime, cint, flt

STATUS_FIELD = 'custom_sos_delivery_status'
WHEN_FIELD = 'custom_sos_delivery_on'
BY_FIELD = 'custom_sos_delivery_by'
PREVIOUS_FIELD = 'custom_sos_previous_job_status'
SERVICE_LINK = 'custom_service_job'


def _shop(company):
    return frappe.db.get_value('Servicing Shop', {'company': company, 'is_active': 1}, 'name')


def _fields(dt):
    return {f.fieldname for f in frappe.get_meta(dt).fields}


def _service_job(invoice, shop):
    if SERVICE_LINK not in _fields(invoice.doctype):
        return None
    name = invoice.get(SERVICE_LINK)
    if not name or not frappe.db.exists('Service Job', name):
        return None
    job = frappe.get_doc('Service Job', name)
    if job.shop != shop or job.customer != invoice.customer:
        frappe.throw('Linked Service Job does not match the invoicing shop and customer.')
    return job


def _stock_handover_recorded(invoice):
    """Service/non-stock invoicing has no stock ledger; goods need a stock movement."""
    # Submitted POS Invoices represent completed counter handovers. ERPNext may
    # consolidate their stock/accounting ledger entries at POS Closing later.
    if invoice.doctype == 'POS Invoice':
        return True
    for row in invoice.get('items') or []:
        if frappe.db.get_value('Item', row.item_code, 'is_stock_item'):
            if not cint(invoice.get('update_stock')) and not row.get('delivery_note'):
                return False
    return True


def _set_if_exists(dt, name, values):
    supported = _fields(dt)
    safe = {k: v for k,v in values.items() if k in supported}
    if safe:
        frappe.db.set_value(dt, name, safe, update_modified=False)


def _allowed_statuses(dt):
    meta = frappe.get_meta(dt)
    field = meta.get_field('status')
    if not field or field.fieldtype != 'Select':
        return []
    return [x.strip() for x in (field.options or '').splitlines() if x.strip()]


def on_invoice_submit(doc, method=None):
    if doc.docstatus != 1 or cint(doc.get('is_return')) or doc.flags.get('sos_submit_without_handover'):
        return
    shop = _shop(doc.company)
    if not shop or not _stock_handover_recorded(doc):
        # Do not call a stock sale delivered when invoice did not move stock
        # and there is no existing Delivery Note on its stock rows.
        return
    when = now_datetime()
    who = frappe.session.user or 'Administrator'
    job = _service_job(doc, shop)
    previous = job.status if job else None
    _set_if_exists(doc.doctype, doc.name, {
        STATUS_FIELD: 'Delivered to Customer', WHEN_FIELD: when,
        BY_FIELD: who, PREVIOUS_FIELD: previous,
    })
    if not job:
        return
    current = str(job.status or '')
    if current.lower() in ('cancelled', 'canceled'):
        frappe.throw('Cancelled Service Job cannot be delivered: ' + job.name)
    updates = {STATUS_FIELD:'Delivered to Customer', WHEN_FIELD:when}
    if 'custom_sos_invoice' in _fields('Service Job'):
        updates['custom_sos_invoice'] = doc.name
    # If a workflow governs the Service Job, preserve its native state.
    workflow = frappe.db.exists('Workflow', {'document_type':'Service Job', 'is_active': 1})
    options = _allowed_statuses('Service Job')
    if not workflow:
        if 'Delivered' in options:
            updates['status'] = 'Delivered'
        elif 'Delivered to Customer' in options:
            updates['status'] = 'Delivered to Customer'
    _set_if_exists('Service Job', job.name, updates)


def on_invoice_cancel(doc, method=None):
    shop = _shop(doc.company)
    if not shop:
        return
    if doc.get(STATUS_FIELD) != 'Delivered to Customer':
        return
    _set_if_exists(doc.doctype, doc.name, {STATUS_FIELD:'Delivery Reversed'})
    job = _service_job(doc, shop)
    if not job:
        return
    # Do not undo delivery if another active submitted invoice is linked.
    other = frappe.db.exists('Sales Invoice', {
        SERVICE_LINK: job.name, 'docstatus': 1, 'name': ['!=',doc.name],
    }) if SERVICE_LINK in _fields('Sales Invoice') else None
    if other:
        return
    previous = doc.get(PREVIOUS_FIELD) or 'Ready to Deliver'
    vals = {STATUS_FIELD:'Delivery Reversed'}
    if 'custom_sos_invoice' in _fields('Service Job'):
        vals['custom_sos_invoice'] = None
    if not frappe.db.exists('Workflow', {'document_type':'Service Job','is_active':1}):
        options = _allowed_statuses('Service Job')
        if job.status in ('Delivered','Delivered to Customer') and previous in options:
            vals['status'] = previous
    _set_if_exists('Service Job', job.name, vals)


def setup_delivery_fields():
    """Idempotent site setup. Creates only supplementary delivery metadata fields."""
    additions = {
        STATUS_FIELD: ('Select', 'Customer Delivery Status', 'Not Delivered\nDelivered to Customer\nDelivery Reversed'),
        WHEN_FIELD: ('Datetime','Delivered On',None),
        BY_FIELD: ('Link','Delivered By','User'),
    }
    installed = []
    doctypes = ['Sales Invoice', 'Service Job']
    if frappe.db.exists('DocType','POS Invoice'):
        doctypes.append('POS Invoice')
    for dt in doctypes:
        changes = dict(additions)
        if dt in ('Sales Invoice', 'POS Invoice'):
            changes[PREVIOUS_FIELD] = ('Data','Previous Service Status',None)
        if dt == 'Service Job':
            changes['custom_sos_invoice'] = ('Data','Delivery Invoice',None)
        anchor = 'customer' if frappe.get_meta(dt).has_field('customer') else 'status'
        for fieldname, (typ, label, options) in changes.items():
            if frappe.get_meta(dt).has_field(fieldname):
                continue
            props = {'doctype':'Custom Field','dt':dt,'fieldname':fieldname,'label':label,
                     'fieldtype':typ,'insert_after':anchor,'read_only':1,
                     'allow_on_submit':1 if dt!='Service Job' else 0}
            if options:
                props['options'] = options
            frappe.get_doc(props).insert(ignore_permissions=True)
            installed.append(dt+' / '+fieldname)
            anchor = fieldname
        frappe.clear_cache(doctype=dt)
    frappe.db.commit()
    return {'created':installed, 'message':'Installed delivery metadata; previous customer transactions unchanged.'}


@frappe.whitelist(methods=['GET'])
def get_branded_invoice(invoice_name=None, doctype='Sales Invoice'):
    if frappe.session.user == 'Guest':
        frappe.throw('Sign in to print an invoice.', frappe.PermissionError)
    if doctype not in ('Sales Invoice','POS Invoice'):
        frappe.throw('Unsupported invoice type.')
    name = str(invoice_name or '').strip()
    if not name or len(name)>140:
        frappe.throw('A valid Invoice Number is required.')
    inv = frappe.get_doc(doctype,name)
    inv.check_permission('read')
    shop_name = _shop(inv.company)
    if not shop_name:
        frappe.throw('Invoice does not belong to an active SERVICING OS company.')
    shop = frappe.get_doc('Servicing Shop', shop_name)
    shop.check_permission('read')
    company = frappe.get_doc('Company',inv.company)
    company.check_permission('read')
    client_name = frappe.db.get_value('Customer',inv.customer,'customer_name') if inv.customer else None
    customer_mobile = ''
    if inv.customer and frappe.has_permission('Customer','read',inv.customer):
        customer_mobile = frappe.db.get_value('Customer',inv.customer,'mobile_no') or ''
    lines=[]
    for row in inv.get('items') or []:
        lines.append({
            'item_code':row.item_code,'item_name':row.item_name or row.item_code,
            'description':str(row.description or '')[:400],
            'qty':flt(row.qty),'uom':row.uom or row.stock_uom or 'Nos',
            'rate':flt(row.rate),'amount':flt(row.amount),
            'discount_percentage':flt(row.get('discount_percentage')),
            'serial_no':str(row.get('serial_no') or ''),
        })
    taxes=[{'description':t.description or t.account_head or 'Tax',
            'amount':flt(t.tax_amount)} for t in inv.get('taxes') or []]
    payments=[]
    for x in inv.get('payments') or []:
        payments.append({'mode_of_payment':x.get('mode_of_payment') or '', 'amount':flt(x.get('amount'))})
    status = 'CANCELLED' if inv.docstatus==2 else ('DRAFT' if inv.docstatus==0 else ('PAID' if flt(inv.get('outstanding_amount'))<=0 else 'ISSUED'))
    delivery = inv.get(STATUS_FIELD) if STATUS_FIELD in _fields(doctype) else ''
    if not delivery:
        delivery = 'Pending Delivery' if inv.docstatus!=1 else 'Not recorded'
    from servicing_os.api.service_invoice_661 import linked_job
    from servicing_os.api.invoice_payment import can_receive
    return {
        'name':inv.name,'doctype':inv.doctype,'company':company.company_name or company.name,
        'company_address':shop.get('address') or '', 'company_phone':shop.get('phone') or '',
        'company_email':shop.get('email') or '',
        'customer':inv.customer,'customer_name':client_name or inv.customer,
        'customer_phone':customer_mobile,
        'posting_date':str(inv.posting_date or ''),'posting_time':str(inv.get('posting_time') or ''),
        'due_date':str(inv.get('due_date') or ''),
        'currency':inv.currency or company.default_currency or 'BDT',
        'service_job':linked_job(inv) or None,
        'remarks':str(inv.get('remarks') or '')[:400],
        'status':status,'docstatus':inv.docstatus,'delivery_status':delivery,
        'modified':str(inv.modified),
        'can_submit':doctype == 'Sales Invoice' and inv.docstatus == 0 and bool(inv.has_permission('submit')),
        'can_edit':doctype == 'Sales Invoice' and inv.docstatus == 0 and not cint(inv.get('is_return'))
                   and bool(inv.has_permission('write')),
        'can_pay':doctype == 'Sales Invoice' and inv.docstatus == 1 and not cint(inv.get('is_return'))
                  and flt(inv.outstanding_amount) > 0 and can_receive(),
        'net_total':flt(inv.net_total),'grand_total':flt(inv.grand_total),
        'discount_amount':flt(inv.discount_amount),
        'additional_discount_percentage':flt(inv.get('additional_discount_percentage')),
        'total_taxes_and_charges':flt(inv.get('total_taxes_and_charges')),
        'outstanding_amount':flt(inv.get('outstanding_amount')),
        'paid_amount':max(0,flt(inv.grand_total)-flt(inv.get('outstanding_amount'))) if inv.docstatus==1 else 0,
        'items':lines,'taxes':taxes,'payments':payments,
        'qr_reference':f'{inv.doctype} | {inv.name} | {inv.company} | {inv.posting_date} | {inv.currency} {flt(inv.grand_total):.2f}',
    }
