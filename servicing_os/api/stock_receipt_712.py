"""SERVICING OS V7.12: controlled spare-part Material Receipt + buying/selling prices.

Receipts are explicit, never fabricated by checkout. For supplier purchases use
ERPNext Purchase Receipt instead. Serial/batch items require native ERPNext UI.
"""
import re
import frappe
from frappe.utils import flt
from servicing_os.api.parts_workbench_708 import _scope, _manager_require


def _validate_item(code):
    code = str(code or '').strip()
    if not code or len(code) > 140:
        frappe.throw('Select a valid stock Item Code.')
    item = frappe.get_doc('Item', code)
    if item.disabled or not item.is_stock_item or item.has_serial_no or item.has_batch_no:
        frappe.throw('Choose an active non-serialized, non-batch stock item. Serial/batch items must be received through ERPNext.')
    item.check_permission('read')
    return item


def _amount(raw, label, strictly_positive=True):
    try:
        n = float(raw)
    except (TypeError, ValueError):
        frappe.throw(label + ' must be numeric.')
    import math
    if not math.isfinite(n) or n < 0 or n > 1e9 or (strictly_positive and n <= 0):
        frappe.throw('Enter a valid ' + label + '.')
    return flt(n)


def _price_lists():
    rows = frappe.get_all('Price List', filters={'enabled':1}, fields=['name','buying','selling','currency'], limit_page_length=200)
    return [dict(x) for x in rows]


def _get_scope(job_name):
    job, ctx, warehouse = _scope(job_name)
    job.check_permission('write')
    if job.status in ('Delivered','Cancelled','Canceled'):
        frappe.throw('Closed Service Jobs cannot receive parts via this workflow.')
    return job, ctx, warehouse


@frappe.whitelist(methods=['GET'])
def receipt_context(job_name, item_code=''):
    _manager_require(create=True)
    job, ctx, warehouse = _get_scope(job_name)
    item = _validate_item(item_code) if item_code else None
    available = 0.0
    if item:
        b = frappe.db.get_value('Bin', {'item_code':item.name, 'warehouse':warehouse}, 'actual_qty')
        available = flt(b)
    return {'service_job':job.name, 'company':ctx['company'], 'warehouse':warehouse,
            'currency':frappe.db.get_value('Company',ctx['company'],'default_currency') or 'BDT',
            'item': {'item_code':item.name, 'item_name':item.item_name, 'uom':item.stock_uom, 'available':available} if item else None,
            'price_lists':_price_lists(),
            'can_submit': bool(frappe.has_permission('Stock Entry', 'submit')),
            'can_update_prices': bool(frappe.has_permission('Item Price', 'create') or
                                      frappe.has_permission('Item Price', 'write'))}


@frappe.whitelist(methods=['GET'])
def suggest_receipt_items(job_name, q=''):
    _manager_require(create=True)
    _, _, warehouse = _get_scope(job_name)
    if not frappe.has_permission('Item', 'read'):
        frappe.throw('Item read permission required.', frappe.PermissionError)
    options = {
        'filters': {'disabled': 0, 'is_stock_item': 1, 'has_serial_no': 0, 'has_batch_no': 0},
        'fields': ['name', 'item_name', 'stock_uom'],
        'order_by': 'modified desc, name asc',
        'limit_page_length': 8,
    }
    query = str(q or '').strip()[:80]
    if query:
        pattern = '%' + query.replace('%', r'\%').replace('_', r'\_') + '%'
        options['or_filters'] = {'name': ['like', pattern], 'item_name': ['like', pattern]}
    items = frappe.get_list('Item', **options)
    if not items:
        return {'items': []}
    bins = frappe.get_all(
        'Bin', filters={'warehouse': warehouse, 'item_code': ['in', [item.name for item in items]]},
        fields=['item_code', 'actual_qty'],
    )
    on_hand = {row.item_code: flt(row.actual_qty) for row in bins}
    return {'items': [
        {'item_code': item.name, 'item_name': item.item_name, 'uom': item.stock_uom,
         'on_hand': on_hand.get(item.name, 0)}
        for item in items
    ]}


def _upsert_price(item_code, price_list, price, currency, direction):
    if not price_list:
        frappe.throw('Select a %s Price List.' % direction)
    pl=frappe.get_doc('Price List',price_list)
    if pl.enabled == 0 or not getattr(pl,direction,False):
        frappe.throw('The selected Price List is not an active %s list.' % direction)
    if pl.currency and pl.currency!=currency:
        frappe.throw('Price List currency differs from company currency.')
    existing = frappe.get_all('Item Price', filters={'item_code':item_code,'price_list':price_list,
                        'customer':['is','not set'],'supplier':['is','not set']},
                        fields=['name'],limit_page_length=3)
    if len(existing)>1:
        frappe.throw('Multiple base Item Prices exist; update prices manually in ERPNext.')
    if existing:
        doc=frappe.get_doc('Item Price', existing[0].name)
        doc.check_permission('write')
        doc.price_list_rate=price
        doc.save()
    else:
        if not frappe.has_permission('Item Price','create'):
            frappe.throw('Item Price create permission required.',frappe.PermissionError)
        doc=frappe.get_doc({'doctype':'Item Price','item_code':item_code,'price_list':price_list,
                            'price_list_rate':price,'currency':currency})
        doc.insert()
    return doc.name


@frappe.whitelist(methods=['POST'])
def receive_part(job_name, item_code, qty, buying_rate, selling_rate,
                 buying_price_list, selling_price_list, reason, confirmation, request_key):
    """Explicit manager-confirmed receipt; reusing request_key never repeats the receipt.

    Native Stock Entry + Item Price changes are committed or rolled back together.
    """
    _manager_require(create=True,submit=True)
    job, ctx, warehouse = _get_scope(job_name)
    item=_validate_item(item_code)
    q=_amount(qty,'quantity')
    cost=_amount(buying_rate,'buying / valuation rate')
    sale=_amount(selling_rate,'selling rate')
    if q>100000:
        frappe.throw('Quantity is above the supported limit.')
    if buying_price_list == selling_price_list:
        frappe.throw('Use distinct Buying and Selling Price Lists so one rate cannot overwrite the other.')
    reason=str(reason or '').strip()
    if len(reason)<12 or len(reason)>250:
        frappe.throw('Enter an auditable stock receipt reason (12–250 characters).')
    if str(confirmation or '').strip() != 'RECEIVE '+item.name:
        frappe.throw('Confirm by typing RECEIVE '+item.name)
    key=str(request_key or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9-]{12,64}',key):
        frappe.throw('Invalid stock receipt request key.')
    # Lock the job to serialize concurrent submits for this shop/work order.
    frappe.db.sql('SELECT name FROM `tabService Job` WHERE name=%s FOR UPDATE',(job.name,))
    marker='[SOS712:'+key+']'
    duplicates=frappe.get_all('Stock Entry', filters={'company':ctx['company'],'purpose':'Material Receipt',
                       'remarks':['like','%'+marker+'%'],'docstatus':['!=',2]},
                       fields=['name','docstatus'],limit_page_length=3)
    if duplicates:
        if len(duplicates)>1:
            frappe.throw('Duplicate receipt keys found; review Stock Entry register.')
        return {'stock_entry':duplicates[0].name,'docstatus':duplicates[0].docstatus,
                'already_recorded':True,'stock_added':duplicates[0].docstatus==1}
    # Validate price lists BEFORE posting stock (transactional rollback also applies).
    pls={p['name']:p for p in _price_lists()}
    currency=frappe.db.get_value('Company',ctx['company'],'default_currency') or 'BDT'
    for name,direction in ((buying_price_list,'buying'),(selling_price_list,'selling')):
        pl=pls.get(name)
        if not pl or not pl.get(direction) or (pl.get('currency') and pl['currency']!=currency):
            frappe.throw('Choose an enabled '+direction+' Price List in '+currency)
    if not (frappe.has_permission('Item Price','create') or frappe.has_permission('Item Price','write')):
        frappe.throw('Item Price create/write permission required.',frappe.PermissionError)
    doc=frappe.get_doc({'doctype':'Stock Entry','stock_entry_type':'Material Receipt',
        'purpose':'Material Receipt','company':ctx['company'],
        'remarks': reason+' | Repair '+job.name+' '+marker,
        'items':[{'item_code':item.name,'qty':q,'t_warehouse':warehouse,
                  'basic_rate':cost,'uom':item.stock_uom,'conversion_factor':1}]})
    doc.insert()
    doc.submit()
    _upsert_price(item.name,buying_price_list,cost,currency,'buying')
    _upsert_price(item.name,selling_price_list,sale,currency,'selling')
    return {'stock_entry':doc.name,'docstatus':doc.docstatus,'stock_added':True,
            'already_recorded':False,'warehouse':warehouse,
            'purchase_valuation_rate':cost,'selling_price':sale}
