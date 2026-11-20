"""SERVICING OS 6.54 unified ERPNext draft invoices: retail, used laptops, service.

All writes create DRAFT Sales Invoice documents only. Native ERPNext submission,
stock valuation, tax and payment workflows remain authoritative. No bypass permissions.
"""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import frappe
from servicing_os.api.service_invoice_661 import active_sale_invoice_names
from servicing_os.revenue_streams import KIND_TO_STREAM, STREAM_FIELD
from frappe.utils import nowdate

LINK_FIELD = "custom_service_job"
D2 = Decimal('0.01')
KINDS = ('retail', 'used', 'service')


def auth():
    if frappe.session.user == 'Guest':
        frappe.throw('Sign in to SERVICING OS.', frappe.PermissionError)


def dec(value, name, *, minimum=Decimal('0'), maximum=Decimal('100000000')):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        frappe.throw('Invalid ' + name)
    if not n.is_finite() or n < minimum or n > maximum or n.as_tuple().exponent < -2:
        frappe.throw(name + ' is outside its allowed range (maximum 2 decimal places)')
    return n


def kind_of(value):
    value = str(value or '').lower().strip()
    if value not in KINDS:
        frappe.throw('Select Retail Sale, Used Laptop, or Service Job.')
    return value


def shop_config():
    auth()
    if not frappe.has_permission('Servicing Shop', 'read'):
        frappe.throw('Servicing Shop read permission required', frappe.PermissionError)
    from servicing_os.api.site_company_706 import site_shop_context

    shop = frappe.get_doc('Servicing Shop', site_shop_context()['shop'])
    shop.check_permission('read')
    for field in ('retail_warehouse','used_laptop_warehouse'):
        w = shop.get(field)
        if not w:
            frappe.throw('Configure the ' + field.replace('_',' ') + ' in Servicing Shop.')
        info = frappe.db.get_value('Warehouse',w,['company','is_group','disabled'],as_dict=True)
        if not info or info.company != shop.company or info.is_group or info.disabled:
            frappe.throw('Invalid configured warehouse: ' + w)
    return shop


def read_permission(doctype, name=None):
    auth()
    if not frappe.has_permission(doctype, 'read', name):
        frappe.throw(doctype + ' read permission required', frappe.PermissionError)


@frappe.whitelist(methods=['GET'])
def get_invoice_setup():
    shop = shop_config()
    if not frappe.has_permission('Sales Invoice','create'):
        frappe.throw('Sales Invoice create permission required', frappe.PermissionError)
    jobs = []
    if frappe.has_permission('Service Job','read'):
        jobs = frappe.get_list('Service Job', fields=['name','customer','customer_name','status','shop'],
                              filters={'shop':shop.name}, order_by='creation desc', limit_page_length=150)
    return {'company':shop.company,'currency':frappe.db.get_value('Company',shop.company,'default_currency'),
            'retail_warehouse':shop.retail_warehouse,'used_laptop_warehouse':shop.used_laptop_warehouse,
            'jobs':[dict(j) for j in jobs], 'draft_only': True}


@frappe.whitelist(methods=['GET'])
def search_invoice_customers(q=''):
    read_permission('Customer')
    q = str(q or '').strip()[:80]
    if len(q) < 1:return {'results':[]}
    # Frappe get_list enforces row-level permissions.
    rows = frappe.get_list('Customer',
      or_filters={'name':['like','%'+q+'%'],'customer_name':['like','%'+q+'%']},
      fields=['name','customer_name','mobile_no'], order_by='modified desc', limit_page_length=12)
    return {'results':[dict(x) for x in rows]}


@frappe.whitelist(methods=['GET'])
def search_invoice_items(q='', invoice_kind='retail', page=1, page_size=20):
    """Permission-checked item catalog, including zero-stock products."""
    kind=kind_of(invoice_kind)
    shop=shop_config()
    read_permission('Item')
    q=str(q or '').strip()[:80]
    try: page=max(1,min(10000,int(page)))
    except (TypeError,ValueError): page=1
    try: page_size=max(1,min(20,int(page_size)))
    except (TypeError,ValueError): page_size=20
    filters={'disabled':0,'is_sales_item':1}
    if kind=='service': pass  # SOS_REPAIR_PARTS_BILLING_712 · service labour + repair parts
    elif kind=='used': filters['is_stock_item']=1
    opts={
        'filters':filters,
        'fields':['name','item_name','stock_uom','is_stock_item','has_serial_no'],
        'order_by':'modified desc, name asc',
        'start':(page-1)*page_size,
        'limit_page_length':page_size+1,
    }
    if q:
        pattern='%'+q.replace('%',r'\%').replace('_',r'\_')+'%'
        opts['or_filters']={'name':['like',pattern],'item_name':['like',pattern]}
    rows=frappe.get_list('Item',**opts)
    has_next=len(rows)>page_size
    warehouse=shop.used_laptop_warehouse if kind=='used' else shop.retail_warehouse
    if kind=='service':
        warehouse=frappe.db.get_value('Servicing Shop',shop.name,'spare_parts_warehouse') or shop.retail_warehouse
    results=[]
    for item in rows[:page_size]:
        record=dict(item)
        record['stock_qty']=None
        if record.get('is_stock_item'):
            qty=frappe.db.get_value('Bin',{'warehouse':warehouse,'item_code':record['name']},'actual_qty') or 0
            record['stock_qty']=float(qty)
        # Include zero-stock items for browsing and searching. ERPNext still validates sales.
        results.append(record)
    return {'results':results,'warehouse':warehouse,'page':page,'page_size':page_size,'has_next':has_next}


def checked_job(job_name, shop):
    if not frappe.has_permission('Service Job','read'):
        frappe.throw('Service Job permission required',frappe.PermissionError)
    name=str(job_name or '').strip()
    if not name:frappe.throw('Choose a saved Service Job.')
    job=frappe.get_doc('Service Job',name)
    job.check_permission('read')
    if job.shop!=shop.name or not job.customer:
        frappe.throw('Selected Service Job does not belong to this shop or has no linked Customer.')
    if not frappe.get_meta('Sales Invoice').has_field(LINK_FIELD):
        frappe.throw('Missing Sales Invoice custom_service_job field.')
    return job



# SERVICING_OS_WARRANTY_672: valid whole-day warranty, never infer coverage.
def _sos672_warranty_days(raw):
    value=str(raw if raw is not None else '').strip()
    if not value.isdigit():return 0
    count=int(value)
    return count if 0 < count <= 36500 else 0


# SERVICING_OS_WARRANTY_674 — save manual warranty to an empty Item Master.
# The invoice must have been inserted successfully before this helper runs.
# No ignore_permissions, direct SQL UPDATE, or independent commit is used.
def _sos674_promote_manual_warranties(submitted_lines, saved_invoice):
    stored = list(saved_invoice.get('items') or [])
    if len(submitted_lines) != len(stored):
        frappe.throw('Invoice item count changed; manual warranty could not be synchronized.')

    requested = {}
    for entered, saved in zip(submitted_lines, stored):
        if not isinstance(entered, dict):
            frappe.throw('Unexpected warranty line input.')
        if str(entered.get('warranty_choice') or '').strip().lower() != 'manual':
            continue
        code = str(entered.get('item_code') or '').strip()
        if not code or code != saved.item_code:
            frappe.throw('Invoice item order changed; cannot safely update Item warranty.')
        days = _sos672_warranty_days(entered.get('warranty_period_days'))
        if not days:
            frappe.throw('Enter valid manual warranty days (1–36500) for ' + code)
        # Confirm that the invoice line really saved these warranty days.
        if int(saved.get('custom_sos_warranty_period_days') or 0) != days:
            # The Item Master may have supplied a different (higher-priority)
            # warranty between request preparation and invoice save.
            continue
        if code in requested and requested[code] != days:
            frappe.throw('Conflicting manual warranty days for the same Item: ' + code)
        requested[code] = days

    updated = []
    for code in sorted(requested):
        days = requested[code]
        # Lock each Item record inside the invoice transaction. Concurrent
        # checkouts must never overwrite a warranty another user has set.
        locked = frappe.db.sql(
            'SELECT warranty_period FROM `tabItem` WHERE name = %s FOR UPDATE',
            (code,), as_dict=True
        )
        if len(locked) != 1:
            frappe.throw('Item does not exist: ' + code)
        current = str(locked[0].get('warranty_period') or '').strip()
        if current and current != '0':
            continue  # Item Master warranty takes priority: never overwrite.
        item_doc = frappe.get_doc('Item', code)
        item_doc.check_permission('write')
        recheck = str(item_doc.get('warranty_period') or '').strip()
        if recheck and recheck != '0':
            continue
        item_doc.set('warranty_period', str(days))
        item_doc.save()  # normal Item validation/audit; same transaction
        updated.append({'item_code': code, 'warranty_period_days': days})
    return updated

@frappe.whitelist(methods=['POST'])
def create_unified_invoice_draft(invoice_kind=None, customer=None, job_name=None, items=None,
                                 discount_mode='none', discount_value=0, remarks=''):
    kind=kind_of(invoice_kind)
    shop=shop_config()
    if not frappe.has_permission('Sales Invoice','create'):
        frappe.throw('Sales Invoice create permission required',frappe.PermissionError)
    if not frappe.has_permission('Item','read'):
        frappe.throw('Item read permission required',frappe.PermissionError)
    job=None
    if kind=='service':
        job=checked_job(job_name,shop)
        customer=job.customer
        # Serializes this job's invoices without locking unrelated sales.
        frappe.db.sql('SELECT name FROM `tabService Job` WHERE name=%s FOR UPDATE',(job.name,))
        prior = active_sale_invoice_names(job.name, shop.company)
        if prior:
            frappe.throw('A draft or submitted invoice already exists for this Service Job: '+prior[0])
    name=str(customer or '').strip()
    if not name or not frappe.db.exists('Customer',name):frappe.throw('Choose an existing Customer.')
    read_permission('Customer',name)
    if isinstance(items,str):items=frappe.parse_json(items)
    if not isinstance(items,list) or not 1<=len(items)<=35:
        frappe.throw('Include between 1 and 35 invoice items.')
    warehouse=shop.used_laptop_warehouse if kind=='used' else shop.retail_warehouse
    if kind=='service':
        warehouse=frappe.db.get_value('Servicing Shop',shop.name,'spare_parts_warehouse')
        wh=frappe.db.get_value('Warehouse',warehouse,['company','is_group','disabled'],as_dict=True) if warehouse else None
        if not wh or wh.company!=shop.company or wh.is_group or wh.disabled:
            frappe.throw('Configure a valid active Spare Parts Warehouse for the Servicing Shop.')
    subtotal=Decimal('0')
    bill_lines=[]
    for pos,line in enumerate(items,1):
        if not isinstance(line,dict):frappe.throw('Invalid invoice row '+str(pos))
        code=str(line.get('item_code') or '').strip()
        if not code:frappe.throw('Choose an Item Code at row '+str(pos))
        read_permission('Item',code)
        item=frappe.db.get_value('Item',code,
            ['name','disabled','is_sales_item','is_stock_item','has_serial_no','stock_uom'],as_dict=True)
        if not item or item.disabled or not item.is_sales_item:
            frappe.throw('Row '+str(pos)+' is not an active selling item')
        if kind=='service' and item.is_stock_item and (item.has_serial_no or frappe.db.get_value('Item',item.name,'has_batch_no')):
            frappe.throw('Serial/batch repair parts require ERPNext native stock and invoice processing.')
        if kind=='used' and not item.is_stock_item:
            frappe.throw('Used laptop invoice lines must be stock-tracked Items.')
        qty=dec(line.get('qty'),'Quantity',minimum=Decimal('0.01'),maximum=Decimal('10000'))
        rate=dec(line.get('rate'),'Rate')
        pct=dec(line.get('discount_percentage') or 0,'Line discount %',maximum=Decimal('100'))
        unit_discount=(rate*pct/100).quantize(D2,rounding=ROUND_HALF_UP)
        unit_rate=max(Decimal('0'),rate-unit_discount)
        subtotal+=(unit_rate*qty).quantize(D2,rounding=ROUND_HALF_UP)
        row={'item_code':item.name,'qty':float(qty),'uom':item.stock_uom,
             'price_list_rate':float(rate),'rate':float(unit_rate),
             'discount_percentage':float(pct),'discount_amount':float(unit_discount)}
        if item.is_stock_item:
            row['warehouse']=warehouse
            available=Decimal(str(frappe.db.get_value('Bin',{'warehouse':warehouse,'item_code':item.name},'actual_qty') or 0))
            if kind!='service' and available<qty:frappe.throw('Insufficient stock in '+warehouse+' for '+item.name)
            serial=str(line.get('serial_no') or '').strip()
            if item.has_serial_no:
                parts=[s.strip() for s in re.split(r'[\n,]+',serial) if s.strip()]
                if len(parts)!=int(qty) or qty!=int(qty) or len(set(parts))!=len(parts):
                    frappe.throw('Enter one unique Serial Number per unit for '+item.name)
                # ERPNext v15 submission may additionally need a Serial and Batch Bundle.
                # Preserve serial selection on the draft; never bypass native submit checks.
                row['serial_no']='\n'.join(parts)
            elif serial:
                frappe.throw('Item '+item.name+' is not serial tracked; clear its Serial Number field.')

        # SERVICING_OS_WARRANTY_672: require real per-item warranty choices from new UI.
        # Older clients with no warranty_choice remain backward-compatible.
        choice=str(line.get('warranty_choice') or '').strip().lower()
        if choice and choice not in ('item_master','manual','none'):
            frappe.throw('Invalid warranty choice for '+code)
        item_period=frappe.db.get_value('Item',code,'warranty_period') if frappe.get_meta('Item').has_field('warranty_period') else None
        master_days=_sos672_warranty_days(item_period)
        if master_days > 0:
            days=master_days
            row['custom_sos_warranty_period_days']=days
        elif choice=='manual':
            days=_sos672_warranty_days(line.get('warranty_period_days'))
            if not days:frappe.throw('Enter valid manual warranty days (1–36500) for '+code)
            row['custom_sos_warranty_period_days']=days
        elif choice=='none':
            row['custom_sos_warranty_type']='No Warranty'
            row['custom_sos_warranty_period_days']=0
        elif choice=='item_master':
            frappe.throw('Item Master warranty is not recorded for '+code+'; enter days manually or select No warranty.')
        if choice or master_days:
            invoice_item_meta=frappe.get_meta('Sales Invoice Item')
            required=('custom_sos_warranty_period_days','custom_sos_warranty_type')
            if any(not invoice_item_meta.has_field(field) for field in required):
                frappe.throw('Invoice warranty fields are missing; run setup_warranty_fields() from the 6.59 warranty setup.')
        bill_lines.append(row)
    if subtotal<=0:frappe.throw('Invoice amount must be greater than zero.')
    mode=str(discount_mode or 'none').lower()
    if mode not in ('none','percent','amount'):frappe.throw('Invalid discount mode.')
    d=dec(discount_value or 0,'Additional discount')
    if mode=='none' and d!=0:frappe.throw('Select a discount mode.')
    if mode=='percent' and d>=100:frappe.throw('Additional discount must be less than 100%.')
    if mode=='amount' and d>=subtotal:frappe.throw('Additional discount must be less than the subtotal.')
    meta=frappe.get_meta('Sales Invoice')
    doc={
        'doctype':'Sales Invoice','company':shop.company,'customer':name,
        STREAM_FIELD: KIND_TO_STREAM[kind],
        'currency':frappe.db.get_value('Company',shop.company,'default_currency'),
        'posting_date':nowdate(),'due_date':nowdate(),
        'update_stock':0 if kind=='service' else (1 if any(x.get('warehouse') for x in bill_lines) else 0),
        'remarks':('SERVICING OS | '+{'retail':'RETAIL SALE','used':'USED LAPTOP','service':'SERVICE JOB'}[kind]+
                   (' | '+str(remarks or '').strip()[:360] if remarks else '')),
        'items':bill_lines,
    }
    if kind=='service':doc[LINK_FIELD]=job.name
    if mode!='none' and d>0:
        doc['apply_discount_on']='Net Total'
        if mode=='percent':doc['additional_discount_percentage']=float(d)
        else:doc['discount_amount']=float(d)
    invoice=frappe.get_doc(doc)
    invoice.insert()  # ERPNext native document validations and permissions
    if invoice.docstatus!=0:frappe.throw('Unexpected invoice submission; reverting transaction.')
    if kind=='service' and invoice.get(LINK_FIELD)!=job.name:
        frappe.throw('Service Job reference was not saved.')
    # SERVICING_OS_WARRANTY_674: promote only explicitly entered manual
    # durations, after a successful invoice insert, in the same transaction.
    sos674_updated_item_warranties = _sos674_promote_manual_warranties(items, invoice)
    return {'success':True,'invoice':invoice.name,'invoice_kind':kind,
            'service_job':job.name if job else None, 'company':invoice.company,
            'customer':invoice.customer,'currency':invoice.currency,'net_total':invoice.net_total,
            'grand_total':invoice.grand_total,'discount_amount':invoice.discount_amount,
            'docstatus':0,'submitted':False,'stock_posted':False,
            'message':'Draft saved. Review and submit through the authorized ERPNext process.'}


def invoice_kind(doc):
    if doc.get(LINK_FIELD):return 'service'
    remarks=str(doc.get('remarks') or '')
    if 'SERVICING OS | USED LAPTOP' in remarks:return 'used'
    return 'retail'


@frappe.whitelist(methods=['GET'])
def get_counter_billing_overview(limit=75):
    shop=shop_config()
    read_permission('Sales Invoice')
    limit=max(1,min(150,int(limit or 75)))
    fields=['name','posting_date','customer','company','currency','status','docstatus',
            'grand_total','outstanding_amount','discount_amount','remarks']
    if frappe.get_meta('Sales Invoice').has_field(LINK_FIELD): fields.append(LINK_FIELD)
    docs=frappe.get_list('Sales Invoice',filters={'company':shop.company,'docstatus':['<',2]},
        fields=fields,order_by='creation desc',limit_page_length=limit)
    rows=[]
    for d in docs:
        d=dict(d)
        d['invoice_kind']=invoice_kind(d)
        d['custom_service_job']=d.get(LINK_FIELD)
        rows.append(d)
    return {'invoices':rows,'company':shop.company}


@frappe.whitelist(methods=['GET'])
def get_counter_invoice_detail(invoice_name=None):
    shop=shop_config()
    name=str(invoice_name or '').strip()
    if not name:frappe.throw('Select an Invoice.')
    doc=frappe.get_doc('Sales Invoice',name)
    doc.check_permission('read')
    if doc.company!=shop.company:frappe.throw('Invoice does not belong to this company.')
    from servicing_os.api.service_invoice_661 import linked_job

    return {'name':doc.name,'company':doc.company,'customer':doc.customer,
            'service_job':linked_job(doc) or None,
            'invoice_kind':invoice_kind(doc),'posting_date':str(doc.posting_date),
            'status':doc.status,'docstatus':doc.docstatus,'currency':doc.currency,'modified':str(doc.modified),
            'net_total':doc.net_total,'discount_amount':doc.discount_amount,
            'grand_total':doc.grand_total,'outstanding_amount':doc.outstanding_amount,
            'items':[{'item_code':r.item_code,'item_name':r.item_name,'qty':r.qty,
                     'rate':r.rate,'amount':r.amount,'discount_percentage':r.discount_percentage,
                     'warehouse':r.warehouse,'serial_no':r.serial_no} for r in doc.items]}
