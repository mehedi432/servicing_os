"""SERVICING OS counter services: shop overview, product master, genuine stock intake.

Uses Frappe/ERPNext native Item, Item Price, Purchase Receipt, Serial and Batch Bundle.
No shop screens, ledgers, or fake balances are created by installation.
"""
import re
import json
from decimal import Decimal, InvalidOperation
import frappe
from frappe.utils import flt, nowdate

COMPANY = 'AL MODINA COMPUTERS LIMITED'
WAREHOUSES = ('Stores - AMCL', 'Spare Parts - AMCL', 'Used Laptops - AMCL')
PRICE_LIST = 'Standard Selling'


def _need(dt, perm, doc=None):
    if not frappe.has_permission(dt, ptype=perm, doc=doc):
        frappe.throw('You need %s permission for %s.' % (perm, dt), frappe.PermissionError)


def _value(v, label, minimum=0):
    try:
        x = Decimal(str(v))
        if not x.is_finite() or x < Decimal(str(minimum)):
            raise ValueError()
        return x
    except (ValueError, InvalidOperation, TypeError):
        frappe.throw('Enter a valid %s (minimum %s).' % (label, minimum))


def _warehouse(name):
    if name not in WAREHOUSES:
        frappe.throw('Choose one of the configured shop warehouses.')
    w = frappe.db.get_value('Warehouse', name, ['company', 'is_group', 'disabled'], as_dict=True)
    if not w or w.company != COMPANY or w.is_group or w.disabled:
        frappe.throw('This warehouse is not an enabled stock warehouse for the shop.')
    return name


def _serials(raw):
    if isinstance(raw, list):
        numbers = [str(s).strip() for s in raw]
    else:
        numbers = [s.strip() for s in re.split(r'[\r\n,]+', str(raw or ''))]
    nums = [s for s in numbers if s]
    if len(nums) > 100 or any(len(x) > 140 or '<' in x or '>' in x for x in nums):
        frappe.throw('Use at most 100 valid serial numbers (one per line).')
    if len(set(x.casefold() for x in nums)) != len(nums):
        frappe.throw('The same serial number appears more than once.')
    return nums


def _get_item(code):
    _need('Item', 'read')
    if not frappe.db.exists('Item', code):
        frappe.throw('Product not found. Add the product first.')
    item = frappe.db.get_value('Item', code, ['name', 'item_name', 'is_stock_item', 'has_serial_no',
                'has_batch_no', 'disabled', 'stock_uom'], as_dict=True)
    if not item or not item.is_stock_item or item.disabled or item.has_batch_no:
        frappe.throw('Only enabled, stock-managed non-batch products are supported in this modal.')
    return item


@frappe.whitelist()
def get_shop_home():
    """Non-privileged view: every number is permission-checked and based on real records."""
    result = {'company': COMPANY, 'shops': [], 'warehouses': [], 'recent_jobs': [],
              'job_total': None, 'pending_jobs': None, 'customer_count': None,
              'item_count': None, 'warnings': []}
    if frappe.db.exists('DocType', 'Servicing Shop') and frappe.has_permission('Servicing Shop', 'read'):
        result['shops'] = [dict(r) for r in frappe.get_list('Servicing Shop',
                fields=['name', 'shop_name', 'company', 'is_active', 'retail_warehouse',
                        'spare_parts_warehouse', 'used_laptop_warehouse'],
                filters={'company': COMPANY}, limit_page_length=10)]
    if not result['shops']:
        result['warnings'].append('No accessible Servicing Shop record. Check shop setup and user permissions.')
    if frappe.has_permission('Warehouse', 'read'):
        for name in WAREHOUSES:
            w = frappe.db.get_value('Warehouse', name, ['name', 'is_group', 'disabled'], as_dict=True)
            if w and not w.is_group:
                result['warehouses'].append({'name': name, 'enabled': not bool(w.disabled)})
    if frappe.has_permission('Service Job', 'read') and frappe.db.exists('DocType', 'Service Job'):
        jobs = frappe.get_list('Service Job', fields=['name','status','customer','modified'],
                              order_by='modified desc', limit_page_length=8)
        result['recent_jobs'] = [dict(r) for r in jobs]
        result['job_total'] = len(frappe.get_list('Service Job', fields=['name'],
                                                 limit_page_length=10000))
        result['pending_jobs'] = sum(1 for r in frappe.get_list('Service Job',
                               fields=['status'], limit_page_length=10000)
                               if r.status not in ('Delivered','Cancelled'))
    if frappe.has_permission('Customer', 'read'):
        result['customer_count'] = len(frappe.get_list('Customer', fields=['name'],limit_page_length=10000))
    if frappe.has_permission('Item', 'read'):
        result['item_count'] = len(frappe.get_list('Item', fields=['name'],
                       filters={'is_stock_item':1,'disabled':0},limit_page_length=10000))
    return result


@frappe.whitelist()
def get_product_setup():
    _need('Item', 'read')
    groups = [r.name for r in frappe.get_list('Item Group',
             fields=['name'], filters={'is_group':0}, order_by='name asc', limit_page_length=300)]
    uoms = [r.name for r in frappe.get_list('UOM',fields=['name'],order_by='name asc',limit_page_length=100)]
    brands = []
    if frappe.db.exists('DocType','Brand') and frappe.has_permission('Brand','read'):
        brands = [r.name for r in frappe.get_list('Brand',fields=['name'], limit_page_length=150)]
    supplier_groups = []
    if frappe.has_permission('Supplier Group','read'):
        supplier_groups = [r.name for r in frappe.get_list('Supplier Group',fields=['name'],
                filters={'is_group':0}, order_by='name asc',limit_page_length=100)]
    suppliers = []
    if frappe.has_permission('Supplier','read'):
        suppliers = [dict(r) for r in frappe.get_list('Supplier',
            fields=['name','supplier_name'],filters={'disabled':0},limit_page_length=250)]
    return {'company':COMPANY,'warehouses':[_warehouse(w) for w in WAREHOUSES if frappe.db.exists('Warehouse',w)
                                             and not frappe.db.get_value('Warehouse',w,'is_group')
                                             and not frappe.db.get_value('Warehouse',w,'disabled')],
            'groups':groups, 'uoms':uoms,'brands':brands,'suppliers':suppliers,
            'supplier_groups':supplier_groups, 'can_create_supplier':bool(frappe.has_permission('Supplier','create')),
            'can_create_item':bool(frappe.has_permission('Item','create')),
            'can_create_price':bool(frappe.has_permission('Item Price','create')),
            'can_create_receipt':bool(frappe.has_permission('Purchase Receipt','create')),
            'can_submit_receipt':bool(frappe.has_permission('Purchase Receipt','submit')),
            'price_list':PRICE_LIST}


@frappe.whitelist()
def create_supplier(data):
    _need('Supplier','create')
    payload = json.loads(data) if isinstance(data,str) else (data or {})
    name = ' '.join(str(payload.get('supplier_name') or '').split())
    group = str(payload.get('supplier_group') or '').strip()
    kind = str(payload.get('supplier_type') or 'Company').strip()
    if not 2<=len(name)<=140:
        frappe.throw('Enter supplier name (2–140 characters).')
    if kind not in ('Company','Individual'):
        frappe.throw('Supplier type must be Company or Individual.')
    if not frappe.db.exists('Supplier Group',{'name':group,'is_group':0}):
        frappe.throw('Choose a valid Supplier Group.')
    if frappe.db.exists('Supplier',name) or frappe.db.exists('Supplier',{'supplier_name':name}):
        frappe.throw('Supplier already exists. Select it from the existing list.')
    doc=frappe.get_doc({'doctype':'Supplier','supplier_name':name,
                        'supplier_group':group,'supplier_type':kind})
    doc.insert()
    return {'name':doc.name,'supplier_name':doc.supplier_name}


@frappe.whitelist()
def find_products(search=''):
    _need('Item','read')
    term = str(search or '').strip()[:100]
    if len(term)<2:
        return {'items':[]}
    esc = term.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
    rows = frappe.get_list('Item', fields=['name','item_name','stock_uom','has_serial_no'],
       filters={'disabled':0,'is_stock_item':1,'has_batch_no':0},
       or_filters=[['Item','name','like','%'+esc+'%'],['Item','item_name','like','%'+esc+'%']],
       limit_page_length=25,order_by='modified desc')
    return {'items':[dict(r) for r in rows]}


@frappe.whitelist()
def create_product(data):
    _need('Item','create')
    payload = json.loads(data) if isinstance(data,str) else (data or {})
    name = ' '.join(str(payload.get('item_name') or '').split())
    code = str(payload.get('item_code') or '').strip() or name
    group = str(payload.get('item_group') or '').strip()
    uom = str(payload.get('stock_uom') or '').strip() or 'Nos'
    if not 2<=len(name)<=140 or not 2<=len(code)<=140:
        frappe.throw('Product Name and Product Code must be 2–140 characters.')
    if not frappe.db.exists('Item Group',{'name':group,'is_group':0}):
        frappe.throw('Choose an existing leaf Item Group.')
    if not frappe.db.exists('UOM',uom):
        frappe.throw('Choose a valid stock unit.')
    if frappe.db.exists('Item',code):
        frappe.throw('A product already uses this Item Code. Search and receive the existing product.')
    brand = str(payload.get('brand') or '').strip()
    if brand and not frappe.db.exists('Brand',brand):
        frappe.throw('Choose an existing brand or leave Brand blank.')
    serial = bool(payload.get('has_serial_no'))
    doc = frappe.get_doc({'doctype':'Item','item_code':code,'item_name':name,'item_group':group,
           'stock_uom':uom,'is_stock_item':1,'has_serial_no':int(serial),'has_batch_no':0,
           'is_sales_item':1,'is_purchase_item':1,'disabled':0})
    if brand:
        doc.brand=brand
    barcode = str(payload.get('barcode') or '').strip()
    if barcode:
        if len(barcode)>100:
            frappe.throw('Barcode is too long.')
        if frappe.db.exists('Item Barcode',{'barcode':barcode}):
            frappe.throw('The barcode is already assigned to another product.')
        doc.append('barcodes',{'barcode':barcode})
    warranty = str(payload.get('warranty_period') or '').strip()
    if warranty:
        months = _value(warranty,'warranty period (months)',0)
        if months != int(months) or months > 120:
            frappe.throw('Warranty period must be a whole number of months (0–120).')
        doc.warranty_period=int(months)
    # Specific manufacturer's physical serials are provided only during real receipt.
    # Never invent serials or set a series that could mask missing serials.
    doc.insert()
    rate = str(payload.get('selling_price') or '').strip()
    if rate:
        amount = _value(rate,'selling price',0)
        if not frappe.has_permission('Item Price',ptype='create'):
            frappe.throw('Item Price creation permission is needed when you provide a selling price.')
        if not frappe.db.exists('Price List',PRICE_LIST):
            frappe.throw('Standard Selling price list does not exist.')
        currency = frappe.db.get_value('Price List',PRICE_LIST,'currency')
        price = frappe.get_doc({'doctype':'Item Price','item_code':doc.name,'price_list':PRICE_LIST,
                               'price_list_rate':float(amount),'currency':currency or 'BDT',
                               'selling':1,'uom':uom})
        price.insert()
    return {'item_code':doc.name,'item_name':doc.item_name,'serialized':bool(serial),
            'message':'Product master created. Stock quantity is still zero until a receipt is confirmed.'}


@frappe.whitelist()
def create_receipt_draft(data):
    _need('Purchase Receipt','create')
    _need('Item','read')
    payload = json.loads(data) if isinstance(data,str) else (data or {})
    item = _get_item(str(payload.get('item_code') or '').strip())
    warehouse = _warehouse(str(payload.get('warehouse') or '').strip())
    supplier = str(payload.get('supplier') or '').strip()
    if not supplier or not frappe.db.exists('Supplier',supplier):
        frappe.throw('Choose a registered supplier. Actual purchase receipts require a supplier.')
    if frappe.db.get_value('Supplier', supplier, 'disabled'):
        frappe.throw('The selected supplier is disabled.')
    qty = _value(payload.get('qty'),'quantity',1)
    if qty > 100000 or (item.has_serial_no and (qty != int(qty) or qty > 100)):
        frappe.throw('Serialized quantities must be whole numbers up to 100 per receipt.')
    rate = _value(payload.get('rate'),'actual purchase rate',0)
    nums = _serials(payload.get('serial_numbers'))
    if item.has_serial_no:
        if len(nums)!=int(qty):
            frappe.throw('Enter exactly one unique physical serial number for every unit.')
        for sn in nums:
            if frappe.db.exists('Serial No',sn):
                frappe.throw('Serial No %s already exists.' % sn)
            # v15 may use generated document ids; also check physical serial field.
            if frappe.get_meta('Serial No').has_field('serial_no') and frappe.db.exists('Serial No',{'serial_no':sn}):
                frappe.throw('Physical serial number %s already exists.' % sn)
    elif nums:
        frappe.throw('This product is not serial-tracked. Do not enter serial numbers.')
    detail={'item_code':item.name,'qty':float(qty),'rate':float(rate),'warehouse':warehouse,
            'uom':item.stock_uom,'stock_uom':item.stock_uom,'conversion_factor':1}
    if nums:
        if not frappe.get_meta('Purchase Receipt Item').has_field('serial_no'):
            frappe.throw('This version does not expose a serial number field on receipt items.')
        detail['serial_no']='\n'.join(nums)
    doc = frappe.get_doc({'doctype':'Purchase Receipt','company':COMPANY,'supplier':supplier,
               'posting_date':nowdate(),'set_warehouse':warehouse,'items':[detail],
               'remarks':'SERVICING OS quick stock intake. Confirm the physical goods before submitting.'})
    doc.insert()
    return {'receipt':doc.name,'item_code':item.name,'qty':float(qty),'serialized':bool(item.has_serial_no),
       'serial_count':len(nums),'docstatus':doc.docstatus,
       'message':'Draft saved. Stock is not increased until Confirm Receipt succeeds.'}


def _prepare_serial_bundle(doc, row):
    """Use native v15 Serial and Batch Bundle for physical serials when legacy mode is disabled.

    No side effects are committed unless receipt submission succeeds.
    """
    if not frappe.db.get_value('Item',row.item_code,'has_serial_no'):
        return
    if row.serial_and_batch_bundle:
        return
    nums = _serials(row.serial_no)
    if len(nums)!=int(flt(row.qty)):
        frappe.throw('Serialized receipt needs one physical serial per unit.')
    # v15 legacy serial fields auto-create bundle only with this setting.
    use_legacy = bool(frappe.get_single_value('Stock Settings','use_serial_batch_fields'))
    if use_legacy:
        return
    # Otherwise construct a transaction-specific SABB using native methods.
    # Directly created Serial No records have no warehouse until stock posting.
    from erpnext.stock.serial_batch_bundle import SerialBatchCreation
    internal_ids = []
    for physical in nums:
        if frappe.db.exists('Serial No', physical):
            frappe.throw('Serial number already exists: ' + physical)
        sn = frappe.get_doc({'doctype':'Serial No','serial_no':physical,
                             'item_code':row.item_code,'company':COMPANY})
        sn.insert()  # actual warehouse/status are set by the receipt's stock ledger
        internal_ids.append(sn.name)
    obj = SerialBatchCreation({'item_code':row.item_code,'warehouse':row.warehouse,
         'company':COMPANY,'voucher_type':'Purchase Receipt','voucher_no':doc.name,
         'voucher_detail_no':row.name,'type_of_transaction':'Inward',
         'qty':float(row.qty),'incoming_rate':float(row.rate),'do_not_submit':True})
    bundle = obj.make_serial_and_batch_bundle(serial_nos=internal_ids)
    if not bundle or not bundle.name:
        frappe.throw('Could not create the serial/batch bundle. Receipt not submitted.')
    row.serial_and_batch_bundle=bundle.name
    # With bundle present, the legacy field is not the authoritative serial source.
    row.serial_no=''


@frappe.whitelist()
def confirm_receipt(receipt):
    _need('Purchase Receipt','submit')
    doc = frappe.get_doc('Purchase Receipt',str(receipt or '').strip())
    _need('Purchase Receipt','read',doc)
    if doc.company != COMPANY or doc.docstatus != 0 or len(doc.items)!=1:
        frappe.throw('Only one-line, draft AMCL receipts can be confirmed from this screen.')
    if doc.owner != frappe.session.user and frappe.session.user != 'Administrator' and 'System Manager' not in frappe.get_roles():
        frappe.throw('Only the receipt creator or manager may submit this receipt.')
    # Savepoint protects any newly generated SN/SABB docs if version-specific checks fail.
    sp = 'sos_quick_stock_confirm'
    frappe.db.savepoint(sp)
    try:
        for row in doc.items:
            _prepare_serial_bundle(doc,row)
        doc.save()
        doc.submit()
    except Exception:
        frappe.db.rollback(save_point=sp)
        raise
    return {'receipt':doc.name,'docstatus':doc.docstatus,'status':'Stock received',
            'message':'Receipt submitted. Warehouse stock ledger updated.'}
