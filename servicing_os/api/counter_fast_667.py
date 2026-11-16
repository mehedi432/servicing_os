"""SERVICING OS 6.67: low-latency sales catalog and customer lookup / quick create.

All catalogue reads respect the active Servicing Shop, Item permissions and the
same Selling Price List rules as counter_selling_price_660. Only create_customer
writes a Customer, after explicit POST and native Customer.create permission.
"""
import re
import frappe
from frappe.utils import flt, getdate, nowdate
from servicing_os.api.counter_invoice_654 import shop_config
from servicing_os.api.counter_selling_price_660 import _pricing_list


def _readable_customers():
    if not frappe.has_permission('Customer', 'read'):
        frappe.throw('Customer read permission required.', frappe.PermissionError)


def _clean_mobile(mobile):
    digits = re.sub(r'\D', '', str(mobile or ''))
    if len(digits) == 13 and digits.startswith('8801'):
        digits = '0' + digits[3:]
    if len(digits) != 11 or not digits.startswith('01'):
        frappe.throw('Enter a valid Bangladesh mobile number, e.g. 01XXXXXXXXX.')
    return digits


def _decode_customer(row):
    return {'name': row.name, 'customer_name': row.customer_name or row.name,
            'mobile_no': row.get('mobile_no') or ''}


@frappe.whitelist(methods=['GET'])
def find_customers(q=''):
    shop_config()
    _readable_customers()
    term = str(q or '').strip()[:80]
    if len(term) < 2:
        return {'results': []}
    safe = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    fields = ['name', 'customer_name']
    filters = [['Customer', 'name', 'like', '%'+safe+'%'],
               ['Customer', 'customer_name', 'like', '%'+safe+'%']]
    if frappe.get_meta('Customer').has_field('mobile_no'):
        fields.append('mobile_no')
        filters.append(['Customer', 'mobile_no', 'like', '%'+safe+'%'])
        digits = re.sub(r'\D', '', term)
        if len(digits) >= 10:
            filters.append(['Customer', 'mobile_no', 'like', '%'+digits[-10:]+'%'])
    records = frappe.get_list('Customer', fields=fields, or_filters=filters,
                              order_by='modified desc', limit_page_length=20)
    return {'results': [_decode_customer(r) for r in records]}


def _leaf_default(doctype, requested):
    if requested and frappe.db.exists(doctype, requested):
        return requested
    try:
        return frappe.db.get_value(doctype, {'is_group': 0}, 'name', order_by='creation asc')
    except Exception:
        return None


@frappe.whitelist(methods=['POST'])
def create_customer(customer_name=None, mobile_no=None):
    shop_config()
    if not frappe.has_permission('Customer', 'create'):
        frappe.throw('Your user needs Customer create permission. Ask an administrator.', frappe.PermissionError)
    name = ' '.join(str(customer_name or '').strip().split())
    if not 2 <= len(name) <= 140:
        frappe.throw('Customer name must be 2–140 characters.')
    if any(ord(c) < 32 for c in name):
        frappe.throw('Customer name contains invalid characters.')
    mobile = _clean_mobile(mobile_no)
    _readable_customers()
    existing = frappe.get_list('Customer',
        filters={'mobile_no': ['like', '%'+mobile[-10:]+'%']},
        fields=['name', 'customer_name', 'mobile_no'],limit_page_length=30)
    for row in existing:
        number = re.sub(r'\D', '', str(row.get('mobile_no') or ''))
        if number.endswith(mobile[-10:]):
            return {'created': False, 'customer': _decode_customer(row),
                    'message': 'This mobile already belongs to an existing customer.'}
    group = _leaf_default('Customer Group',
        frappe.db.get_single_value('Selling Settings', 'customer_group'))
    territory = _leaf_default('Territory',
        frappe.db.get_single_value('Selling Settings', 'territory'))
    if not group or not territory:
        frappe.throw('Configure a leaf Customer Group and Territory before creating customers.')
    fields = {'doctype': 'Customer', 'customer_name': name,
              'customer_type': 'Individual', 'customer_group': group, 'territory': territory}
    if frappe.get_meta('Customer').has_field('mobile_no'):
        fields['mobile_no'] = mobile
    customer = frappe.get_doc(fields)
    customer.insert()  # ERPNext mandatory fields, permissions and controller validations.
    return {'created': True, 'customer': {'name': customer.name,
            'customer_name': customer.customer_name, 'mobile_no': customer.get('mobile_no') or mobile},
            'message': 'Customer created.'}


def _batch_prices(items, price_list, currency, company):
    codes = [r.name for r in items]
    if not codes:
        return {}
    meta = frappe.get_meta('Item Price')
    extras = ('uom', 'customer', 'customer_group', 'supplier', 'valid_from', 'valid_upto',
              'batch_no', 'min_qty', 'currency', 'company')
    fields = ['name', 'item_code', 'price_list_rate'] + [x for x in extras if meta.has_field(x)]
    filters = {'item_code': ['in', codes], 'price_list': price_list}
    if meta.has_field('selling'):
        filters['selling'] = 1
    prices = frappe.get_all('Item Price', filters=filters, fields=fields,
                            order_by='creation desc', limit_page_length=1500)
    item_map = {x.name: x for x in items}
    today = getdate(nowdate())
    found = {}
    for p in prices:
        code = p.item_code
        if code in found or code not in item_map:
            continue
        item = item_map[code]
        if p.get('valid_from') and getdate(p.valid_from) > today:
            continue
        if p.get('valid_upto') and getdate(p.valid_upto) < today:
            continue
        if p.get('uom') and p.uom != item.stock_uom:
            continue
        if p.get('currency') and p.currency != currency:
            continue
        if p.get('company') and p.company != company:
            continue
        if p.get('customer') or p.get('customer_group') or p.get('supplier') or p.get('batch_no'):
            continue
        if p.get('min_qty') and flt(p.min_qty) > 1:
            continue
        rate = flt(p.price_list_rate)
        if rate < 0:
            continue
        found[code] = {'rate': rate, 'item_price': p.name}
    return found


@frappe.whitelist(methods=['GET'])
def search_sale_products(q='', page=1):
    shop = shop_config()
    if not frappe.has_permission('Item', 'read'):
        frappe.throw('Item read permission required.', frappe.PermissionError)
    if not (frappe.has_permission('Sales Invoice', 'create') or frappe.has_permission('POS Invoice', 'create')):
        frappe.throw('Sales create permission required.', frappe.PermissionError)
    term = str(q or '').strip()[:80]
    try:
        page = max(1, min(200, int(page)))
    except (ValueError, TypeError):
        page = 1
    safe = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    query = {'filters': {'disabled': 0, 'is_sales_item': 1},
             'fields': ['name', 'item_name', 'stock_uom', 'is_stock_item',
                        'has_serial_no', 'has_batch_no'],
             'order_by': 'item_name asc', 'start': (page-1)*20, 'limit_page_length': 21}
    if term:
        query['or_filters'] = [
            ['Item', 'name', 'like', '%'+safe+'%'],
            ['Item', 'item_name', 'like', '%'+safe+'%']]
    if frappe.get_meta('Item').has_field('has_variants'):
        query['filters']['has_variants'] = 0
    items = frappe.get_list('Item', **query)
    has_next = len(items) > 20
    items = items[:20]
    price_list, currency = _pricing_list(shop)
    prices = _batch_prices(items, price_list, currency, shop.company)
    codes = [r.name for r in items if r.is_stock_item]
    bins = frappe.get_all('Bin', filters={'warehouse': shop.retail_warehouse,
                        'item_code': ['in', codes]},
                        fields=['item_code', 'actual_qty', 'reserved_qty']) if codes else []
    stocks = {b.item_code: max(0, flt(b.actual_qty)-flt(b.reserved_qty)) for b in bins}
    rows = []
    for item in items:
        price = prices.get(item.name)
        rows.append({'name': item.name, 'item_code': item.name, 'item_name': item.item_name,
                     'stock_uom': item.stock_uom, 'is_stock_item': bool(item.is_stock_item),
                     'has_serial_no': bool(item.has_serial_no),
                     'has_batch_no': bool(item.has_batch_no),
                     'stock_qty': stocks.get(item.name, 0) if item.is_stock_item else None,
                     'list_price': price['rate'] if price else None,
                     'price_list': price_list, 'item_price': price['item_price'] if price else None})
    return {'results': rows, 'page': page, 'has_next': has_next,
            'price_list': price_list, 'warehouse': shop.retail_warehouse}

@frappe.whitelist(methods=['GET'])
def get_stock_products(cursor=0):
    """Fast 20-item stock grid for both POS screens with one batch Item Price read."""
    shop = shop_config()
    if not frappe.has_permission('Item', 'read'):
        frappe.throw('Item read permission required.', frappe.PermissionError)
    if not (frappe.has_permission('Sales Invoice', 'create') or frappe.has_permission('POS Invoice', 'create')):
        frappe.throw('Sales create permission required.', frappe.PermissionError)
    try:
        cursor = max(0, min(100000, int(cursor)))
    except (ValueError, TypeError):
        cursor = 0
    scanned = 0
    offset = cursor
    selected = []
    warehouse = shop.retail_warehouse
    while len(selected) < 20 and scanned < 800:
        bins = frappe.get_all('Bin', filters={'warehouse':warehouse,'actual_qty':['>',0]},
            fields=['item_code','actual_qty','reserved_qty'],
            order_by='modified desc, name desc', start=offset, limit_page_length=80)
        if not bins:
            break
        codes = [b.item_code for b in bins]
        allowed = frappe.get_list('Item', filters={
            'name':['in',codes],'disabled':0,'is_sales_item':1},
            fields=['name','item_name','stock_uom','is_stock_item','has_serial_no','has_batch_no','has_variants'],
            limit_page_length=80)
        allow = {x.name:x for x in allowed}
        for b in bins:
            offset += 1; scanned += 1
            i = allow.get(b.item_code)
            available = flt(b.actual_qty) - flt(b.reserved_qty)
            if not i or not i.is_stock_item or i.get('has_variants') or available <= 0:
                continue
            selected.append({'item':i,'available':float(available)})
            if len(selected) >= 20:
                break
        if len(bins) < 80:
            break
    items = [row['item'] for row in selected]
    selling_list, currency = _pricing_list(shop)
    prices = _batch_prices(items, selling_list, currency, shop.company)
    rows = []
    for record in selected:
        i=record['item']
        price=prices.get(i.name)
        rows.append({'name':i.name,'item_code':i.name,'item_name':i.item_name or i.name,
                     'stock_uom':i.stock_uom,'uom':i.stock_uom,'is_stock_item':True,
                     'has_serial_no':bool(i.has_serial_no),'has_batch_no':bool(i.has_batch_no),
                     'stock_qty':record['available'],'list_price':price['rate'] if price else None,
                     'price_list':selling_list,'item_price':price['item_price'] if price else None})
    future = frappe.get_all('Bin', filters={'warehouse':warehouse,'actual_qty':['>',0]},
                            fields=['item_code'],start=offset,limit_page_length=1)
    return {'items':rows,'warehouse':warehouse,'count':len(rows),
            'has_next':bool(future),'next_cursor':offset if future else None}
