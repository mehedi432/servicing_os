"""SERVICING OS Inventory v2 | permission-aware ERPNext v15 Item / Item Price / Bin UI.

Rates are Item Price records in the active currency-matched price lists, not
stock valuation rates. Stock quantities are never edited from Item Master.
"""
import re
from decimal import Decimal, InvalidOperation

import frappe
from frappe.utils import flt, getdate, get_datetime, today

MAX_ITEMS = 2500
MAX_BINS = 15000
MAX_PRICES = 20000


def _company():
    if frappe.session.user == 'Guest':
        frappe.throw('Login required', frappe.PermissionError)
    shops = frappe.get_list('Servicing Shop', filters={'is_active': 1},
                            fields=['name', 'company'], limit_page_length=2)
    if not shops:
        frappe.throw('No active Servicing Shop is accessible to your account')
    if len(shops) > 1:
        frappe.throw('More than one shop is accessible. Configure a single active shop before editing inventory.')
    if not shops[0].company:
        frappe.throw('Active Servicing Shop has no company')
    return shops[0].company


def _warehouses(company):
    return frappe.get_list('Warehouse', filters={'company': company, 'is_group': 0},
                           fields=['name', 'warehouse_name'],
                           order_by='warehouse_name asc', limit_page_length=500)


def _currency(company):
    return frappe.db.get_value('Company', company, 'default_currency') or 'BDT'


def _warranty_field():
    meta = frappe.get_meta('Item')
    if meta.has_field('warranty_period'):
        return 'warranty_period'
    if meta.has_field('custom_servicing_warranty_days'):
        return 'custom_servicing_warranty_days'
    return None


def _price_lists(company):
    currency = _currency(company)
    choices = frappe.get_all('Price List', filters={'enabled': 1, 'currency': currency},
                             fields=['name', 'buying', 'selling', 'currency'],
                             limit_page_length=500)
    buy_default = frappe.db.get_single_value('Buying Settings', 'buying_price_list') or 'Standard Buying'
    sell_default = frappe.db.get_single_value('Selling Settings', 'selling_price_list') or 'Standard Selling'

    def pick(kind, preferred):
        eligible = [p for p in choices if p.get(kind)]
        return next((p.name for p in eligible if p.name == preferred),
                    next((p.name for p in eligible if p.name == ('Standard Buying' if kind == 'buying' else 'Standard Selling')),
                         eligible[0].name if eligible else None))

    return {'buying': pick('buying', buy_default),
            'selling': pick('selling', sell_default), 'currency': currency}


def _can(doctype, permission, doc=None):
    return bool(frappe.has_permission(doctype, permission, doc))


def _price_fields():
    meta = frappe.get_meta('Item Price')
    optional = ['uom', 'customer', 'supplier', 'batch_no', 'min_qty', 'valid_from', 'valid_upto']
    return ['name', 'item_code', 'price_list', 'price_list_rate', 'modified'] + [f for f in optional if meta.has_field(f)]


def _is_general_rate(r, stock_uom):
    if r.get('uom') and r.uom != stock_uom:
        return False
    if r.get('customer') or r.get('supplier') or r.get('batch_no'):
        return False
    if flt(r.get('min_qty')) > 0:
        return False
    if r.get('valid_from') and getdate(r.valid_from) > getdate(today()):
        return False
    if r.get('valid_upto') and getdate(r.valid_upto) < getdate(today()):
        return False
    return True


def _inventory_prices(items, lists):
    if not items or not _can('Item Price', 'read'):
        return {}
    names = list({p for p in (lists.get('buying'), lists.get('selling')) if p})
    if not names:
        return {}
    codes = [i.name for i in items]
    rows = frappe.get_list('Item Price',
        filters={'price_list': ['in', names], 'item_code': ['in', codes]},
        fields=_price_fields(), order_by='modified desc', limit_page_length=MAX_PRICES + 1)
    if len(rows) > MAX_PRICES:
        frappe.throw('Too many Item Price records for a single inventory view; archive duplicates or extend pagination')
    by_code = {i.name: i for i in items}
    result = {}
    for r in rows:
        item = by_code.get(r.item_code)
        if not item or not _is_general_rate(r, item.stock_uom):
            continue
        target = result.setdefault(r.item_code, {})
        if r.price_list == lists['buying'] and 'buying_price' not in target:
            target['buying_price'] = flt(r.price_list_rate)
        if r.price_list == lists['selling'] and 'selling_price' not in target:
            target['selling_price'] = flt(r.price_list_rate)
    return result


@frappe.whitelist(methods=['GET'])
def get_inventory(warehouse=None):
    company = _company()
    if not _can('Item', 'read') or not _can('Bin', 'read'):
        frappe.throw('Item and stock balance read permissions are required', frappe.PermissionError)
    warehouses = _warehouses(company)
    permitted = [w.name for w in warehouses]
    warehouse = str(warehouse or '').strip()
    if warehouse and warehouse not in permitted:
        frappe.throw('Warehouse is unavailable for this shop', frappe.PermissionError)
    selected = [warehouse] if warehouse else permitted

    fields = ['name', 'item_name', 'item_group', 'stock_uom', 'image', 'description',
              'has_serial_no', 'has_batch_no', 'brand', 'modified']
    wf = _warranty_field()
    if wf:
        fields.append(wf)
    items = frappe.get_list('Item', filters={'disabled': 0, 'is_stock_item': 1},
                            fields=fields, order_by='modified desc',
                            limit_page_length=MAX_ITEMS + 1)
    truncated = len(items) > MAX_ITEMS
    items = items[:MAX_ITEMS]
    index = {i.name: i for i in items}
    balances = {}
    if selected and items:
        bins = frappe.get_list('Bin', filters={'warehouse': ['in', selected]},
            fields=['item_code', 'warehouse', 'actual_qty', 'reserved_qty', 'stock_value'],
            limit_page_length=MAX_BINS + 1)
        if len(bins) > MAX_BINS:
            frappe.throw('Stock balance count exceeds limit. Filter to a warehouse.')
        for b in bins:
            if b.item_code not in index:
                continue
            d = balances.setdefault(b.item_code, {'qty': 0, 'reserved': 0, 'value': 0, 'by_warehouse': []})
            d['qty'] += flt(b.actual_qty)
            d['reserved'] += flt(b.reserved_qty)
            d['value'] += flt(b.stock_value)
            if flt(b.actual_qty) or flt(b.reserved_qty):
                d['by_warehouse'].append({'warehouse': b.warehouse, 'qty': flt(b.actual_qty),
                                          'reserved': flt(b.reserved_qty)})

    lists = _price_lists(company)
    prices = _inventory_prices(items, lists)
    result = []
    for it in items:
        b = balances.get(it.name, {'qty': 0, 'reserved': 0, 'value': 0, 'by_warehouse': []})
        p = prices.get(it.name, {})
        raw_days = it.get(wf) if wf else None
        try:
            warranty_days = max(0, int(raw_days or 0))
        except (ValueError, TypeError):
            warranty_days = 0
        result.append({
            'item_code': it.name, 'item_name': it.item_name or it.name,
            'item_group': it.item_group or '', 'stock_uom': it.stock_uom or 'Nos',
            'image': it.image or '', 'description': it.get('description') or '',
            'brand': it.get('brand') or '', 'warranty_days': warranty_days,
            'has_serial_no': int(it.get('has_serial_no') or 0),
            'has_batch_no': int(it.get('has_batch_no') or 0),
            'actual_qty': round(b['qty'], 3), 'reserved_qty': round(b['reserved'], 3),
            'stock_value': round(b['value'], 2), 'by_warehouse': b['by_warehouse'],
            'buying_price': p.get('buying_price'), 'selling_price': p.get('selling_price'),
            'modified': it.modified,
        })
    can_price_read = _can('Item Price', 'read')
    groups = frappe.get_list('Item Group', filters={'is_group': 0}, fields=['name'],
                              order_by='name asc', limit_page_length=500)
    uoms = frappe.get_list('UOM', fields=['name'], order_by='name asc', limit_page_length=500)
    brands = frappe.get_list('Brand', fields=['name'], order_by='name asc', limit_page_length=500)
    return {
        'company': company, 'currency': lists['currency'], 'warehouses': warehouses,
        'price_lists': {'buying': lists['buying'], 'selling': lists['selling']},
        'warranty_supported': bool(wf),
        'groups': [r.name for r in groups], 'uoms': [r.name for r in uoms],
        'brands': [r.name for r in brands],
        'permissions': {
            'create_item': _can('Item', 'create'), 'edit_item': _can('Item', 'write'),
            'price_read': can_price_read,
            'price_edit': can_price_read and _can('Item Price', 'create') and _can('Item Price', 'write'),
            'stock_post': _can('Stock Entry', 'create') and _can('Stock Entry', 'submit'),
        }, 'items': result, 'truncated': truncated,
    }


def _text(value, label, max_length, required=False):
    value = str(value or '').strip()
    if required and not value:
        frappe.throw(label + ' is required')
    if len(value) > max_length:
        frappe.throw(label + ' exceeds ' + str(max_length) + ' characters')
    return value


def _amount(value, label):
    if value is None or str(value).strip() == '':
        return None
    try:
        rate = Decimal(str(value))
    except (InvalidOperation, ValueError):
        frappe.throw(label + ' must be a valid number')
    if not rate.is_finite() or rate < 0 or rate > Decimal('999999999'):
        frappe.throw(label + ' must be between 0 and 999,999,999')
    return float(rate)


def _warranty(value):
    try:
        raw = str(value if value is not None else '0').strip()
        if not re.fullmatch(r'\d{1,5}', raw):
            raise ValueError()
        n = int(raw)
        if n > 36500:
            raise ValueError()
        return n
    except (TypeError, ValueError):
        frappe.throw('Warranty must be an integer number of days between 0 and 36,500')


def _upsert_price(item_code, price_list, amount, uom):
    if amount is None:
        return
    if not price_list:
        frappe.throw('Configure an enabled company-currency price list in ERPNext first')
    fields = _price_fields()
    prices = frappe.get_list('Item Price', filters={'item_code': item_code, 'price_list': price_list},
                             fields=fields, limit_page_length=501)
    if len(prices) > 500:
        frappe.throw('Too many prices for this item. Review ERPNext Item Price records first.')
    matches = [r for r in prices if _is_general_rate(r, uom)]
    exact = [r for r in matches if r.get('uom') == uom]
    candidates = exact if exact else [r for r in matches if not r.get('uom')]
    # Never silently modify an arbitrary customer / supplier / quantity-specific rate.
    if len(candidates) > 1:
        frappe.throw('Multiple active general Item Prices found in ' + price_list + '. Resolve the duplicates in ERPNext first.')
    if candidates:
        if not _can('Item Price', 'write', frappe.get_doc('Item Price', candidates[0].name)):
            frappe.throw('No permission to update Item Price', frappe.PermissionError)
        doc = frappe.get_doc('Item Price', candidates[0].name)
        doc.price_list_rate = amount
        doc.save()
    else:
        if not _can('Item Price', 'create'):
            frappe.throw('No permission to create Item Price', frappe.PermissionError)
        doc = frappe.get_doc({'doctype': 'Item Price', 'item_code': item_code,
                              'price_list': price_list, 'uom': uom,
                              'price_list_rate': amount})
        doc.insert()


@frappe.whitelist(methods=['POST'])
def save_product(data=None):
    """Add/update catalog data & general prices atomically within one Frappe POST."""
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if not isinstance(data, dict):
        frappe.throw('A product form is required')
    _company()
    editing = _text(data.get('original_item_code'), 'Original SKU', 140)
    item_name = _text(data.get('item_name'), 'Product name', 140, required=True)
    item_group = _text(data.get('item_group'), 'Category', 140, required=True)
    stock_uom = _text(data.get('stock_uom'), 'Unit of measure', 140, required=True)
    brand = _text(data.get('brand'), 'Brand', 140)
    description = _text(data.get('description'), 'Description', 10000)
    image = _text(data.get('image'), 'Image URL', 500)
    if image and not (image.startswith('/files/') or image.startswith('/private/files/')
                      or image.startswith('https://')):
        frappe.throw('Image must use an HTTPS URL or a valid Frappe /files/ path')
    if not frappe.db.exists('Item Group', item_group) or frappe.db.get_value('Item Group', item_group, 'is_group'):
        frappe.throw('Choose a valid leaf Item Group')
    if not frappe.db.exists('UOM', stock_uom):
        frappe.throw('Choose a valid unit of measure')
    if brand and not frappe.db.exists('Brand', brand):
        frappe.throw('Choose an existing Brand or leave it blank')
    wf = _warranty_field()
    if wf is None:
        frappe.throw('Item warranty field is unavailable on this ERPNext installation')
    days = _warranty(data.get('warranty_days'))
    buying = _amount(data.get('buying_price'), 'Buying price')
    selling = _amount(data.get('selling_price'), 'Selling price')
    lists = _price_lists(_company())
    if (buying is not None or selling is not None) and not (_can('Item Price', 'read') and
                                                             _can('Item Price', 'create') and
                                                             _can('Item Price', 'write')):
        frappe.throw('Item Price read/create/write permissions are required to save prices', frappe.PermissionError)
    if (buying is not None or selling is not None) and lists['buying'] and lists['buying'] == lists['selling']:
        frappe.throw('Buying and selling must use separate Price Lists')
    if buying is not None and not lists['buying']:
        frappe.throw('No enabled buying Price List matches company currency ' + lists['currency'])
    if selling is not None and not lists['selling']:
        frappe.throw('No enabled selling Price List matches company currency ' + lists['currency'])

    if editing:
        item = frappe.get_doc('Item', editing)
        if not _can('Item', 'write', item):
            frappe.throw('Item write permission is required', frappe.PermissionError)
        if not item.is_stock_item or item.disabled:
            frappe.throw('This is not an active inventory item')
        loaded_modified = data.get('original_modified')
        if not loaded_modified or get_datetime(loaded_modified) != get_datetime(item.modified):
            frappe.throw('This product was changed by another user. Refresh the Inventory view before editing.')
    else:
        if not _can('Item', 'create'):
            frappe.throw('Item create permission is required', frappe.PermissionError)
        code = _text(data.get('item_code'), 'Item code', 140)
        if not code:
            from frappe.model.naming import make_autoname
            code = make_autoname('SOS-ITEM-.#####')
        if frappe.db.exists('Item', code):
            frappe.throw('This item code is already used: ' + code)
        # Prevent accidental duplicate product names when the operator ignores
        # autocomplete; editing an existing product does not hit this guard.
        possible = frappe.get_list('Item', filters={'item_name':item_name, 'disabled':0},
                                   fields=['name','item_name'], limit_page_length=10)
        if any(str(p.item_name or '').strip().casefold() == item_name.casefold() for p in possible):
            frappe.throw('A product with this name already exists. Select it from the product-name suggestions instead.')
        item = frappe.new_doc('Item')
        item.item_code = code
        item.is_stock_item = 1
        item.is_sales_item = 1
        item.is_purchase_item = 1
    item.item_name = item_name
    item.item_group = item_group
    item.stock_uom = stock_uom
    item.brand = brand or None
    item.description = description or None
    item.image = image or None
    item.set(wf, str(days))
    if editing:
        item.save()
    else:
        item.insert()
    if buying is not None:
        _upsert_price(item.name, lists['buying'], buying, item.stock_uom)
    if selling is not None:
        _upsert_price(item.name, lists['selling'], selling, item.stock_uom)
    return {'item_code': item.name, 'created': not bool(editing), 'modified': str(item.modified),
            'buying_price_list': lists['buying'], 'selling_price_list': lists['selling']}


@frappe.whitelist(methods=['POST'])
def post_stock_movement(item_code=None, warehouse=None, qty=None,
                        movement=None, basic_rate=None, remarks=None):
    company = _company()
    if not (_can('Stock Entry', 'create') and _can('Stock Entry', 'submit')):
        frappe.throw('Stock Entry create and submit permissions are required', frappe.PermissionError)
    movement = str(movement or '').strip().lower()
    if movement not in ('receive', 'issue'):
        frappe.throw('Movement must be receive or issue')
    allowed = {w.name for w in _warehouses(company)}
    if warehouse not in allowed:
        frappe.throw('Choose a permitted warehouse in this shop', frappe.PermissionError)
    amount = _amount(qty, 'Quantity')
    if amount is None or amount <= 0 or amount > 9999999:
        frappe.throw('Enter a positive quantity within the permitted limit')
    if not item_code:
        frappe.throw('Choose an item')
    item = frappe.get_doc('Item', item_code)
    if not _can('Item', 'read', item):
        frappe.throw('No Item read permission', frappe.PermissionError)
    if item.disabled or not item.is_stock_item:
        frappe.throw('Choose an active stock item')
    if item.has_serial_no or item.has_batch_no:
        frappe.throw('Serialized/batch items require their dedicated ERPNext stock workflow')

    line = {'item_code': item.name, 'qty': amount, 'uom': item.stock_uom,
            'stock_uom': item.stock_uom, 'conversion_factor': 1}
    if movement == 'receive':
        valuation = _amount(basic_rate, 'Receipt valuation rate')
        if valuation is None or valuation <= 0:
            frappe.throw('Receipt valuation must be greater than zero')
        line.update({'t_warehouse': warehouse, 'basic_rate': valuation})
        purpose = 'Material Receipt'
    else:
        present = flt(frappe.db.get_value('Bin', {'item_code': item.name,
                                                  'warehouse': warehouse}, 'actual_qty') or 0)
        if amount > present:
            frappe.throw('Insufficient physical stock in this warehouse')
        line['s_warehouse'] = warehouse
        purpose = 'Material Issue'
    entry = frappe.get_doc({'doctype': 'Stock Entry', 'company': company,
                            'stock_entry_type': purpose, 'purpose': purpose,
                            'remarks': _text(remarks, 'Remarks', 1000),
                            'items': [line]})
    entry.insert()
    entry.submit()
    return {'stock_entry': entry.name, 'docstatus': entry.docstatus,
            'movement': movement, 'item_code': item.name,
            'qty': amount, 'warehouse': warehouse}


@frappe.whitelist(methods=['POST'])
def set_product_image(item_code=None, file_url=None):
    """Attach only the public image uploaded onto this exact Item document."""
    _company()
    if not item_code:
        frappe.throw('Product code is required')
    item = frappe.get_doc('Item', item_code)
    if not _can('Item', 'write', item):
        frappe.throw('Item write permission is required', frappe.PermissionError)
    file_url = _text(file_url, 'Uploaded file URL', 500, required=True)
    if not file_url.startswith('/files/'):
        frappe.throw('Upload must be a public Frappe image file')
    fname = frappe.db.exists('File', {
        'file_url': file_url, 'attached_to_doctype': 'Item',
        'attached_to_name': item_code, 'is_private': 0,
    })
    if not fname:
        frappe.throw('Uploaded file is not attached to this Item')
    file = frappe.get_doc('File', fname)
    filename = str(file.file_name or file_url).lower()
    if not filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
        frappe.throw('Only PNG, JPG or WebP files are supported')
    item.image = file_url
    item.save()
    return {'item_code': item.name, 'image': item.image}


def inventory_preflight():
    """Read-only bench smoke check: bench --site servicing.local execute ...inventory_preflight"""
    company = _company()
    lists = _price_lists(company)
    warehouses = _warehouses(company)
    notes = []
    if not _warranty_field():
        notes.append('Item warranty field is missing')
    if not lists['buying']:
        notes.append('Set an enabled buying Price List in ' + lists['currency'])
    if not lists['selling']:
        notes.append('Set an enabled selling Price List in ' + lists['currency'])
    if lists['buying'] and lists['buying'] == lists['selling']:
        notes.append('Buying and selling Price Lists should be separate')
    if not warehouses:
        notes.append('No accessible leaf Warehouses in the shop Company')
    if not frappe.get_list('Item Group', filters={'is_group': 0}, fields=['name'], limit_page_length=1):
        notes.append('No accessible leaf Item Group for product creation')
    if not frappe.get_list('UOM', fields=['name'], limit_page_length=1):
        notes.append('No accessible UOM for product creation')
    return {'ready': not notes, 'company': company, 'currency': lists['currency'],
            'buying_price_list': lists['buying'], 'selling_price_list': lists['selling'],
            'warranty_field': _warranty_field(), 'warehouses': len(warehouses),
            'notes': notes}


@frappe.whitelist(methods=['GET'])
def search_inventory_items(q='', limit=12):
    """Permission-filtered suggestions for product name and Restock autocomplete."""
    _company()
    if not _can('Item', 'read'):
        frappe.throw('Item read permission is required', frappe.PermissionError)
    q = _text(q, 'Search', 140)
    try:
        limit = max(1, min(20, int(limit)))
    except (TypeError, ValueError):
        limit = 12
    filters = {'disabled': 0, 'is_stock_item': 1}
    kwargs = {}
    if q:
        q_escaped = q.replace('%', r'\%').replace('_', r'\_')
        pattern = '%' + q_escaped + '%'
        kwargs['or_filters'] = {'item_name':['like', pattern], 'name':['like', pattern]}
    rows = frappe.get_list('Item', filters=filters, fields=['name', 'item_name', 'item_group', 'brand'],
                           order_by='modified desc', limit_page_length=limit, **kwargs)
    return [{'item_code':r.name, 'item_name':r.item_name or r.name,
             'item_group':r.item_group or '', 'brand':r.brand or ''} for r in rows]


@frappe.whitelist(methods=['GET'])
def get_inventory_item(item_code=None):
    """Load a fresh product for safe edits, including current price-list rates."""
    _company()
    code = _text(item_code, 'Item code', 140, required=True)
    item = frappe.get_doc('Item', code)
    if not _can('Item', 'read', item):
        frappe.throw('Item read permission required', frappe.PermissionError)
    if item.disabled or not item.is_stock_item:
        frappe.throw('This product is inactive or not a stock item')
    company = _company()
    lists = _price_lists(company)
    data = _inventory_prices([item], lists).get(item.name, {})
    wf = _warranty_field()
    return {
        'item_code':item.name, 'item_name':item.item_name or item.name,
        'item_group':item.item_group or '', 'stock_uom':item.stock_uom or 'Nos',
        'brand':item.brand or '', 'description':item.description or '',
        'image':item.image or '', 'modified':str(item.modified),
        'warranty_days':int(item.get(wf) or 0) if wf else 0,
        'buying_price':data.get('buying_price') if _can('Item Price', 'read') else None,
        'selling_price':data.get('selling_price') if _can('Item Price', 'read') else None,
        'has_serial_no':int(item.has_serial_no or 0), 'has_batch_no':int(item.has_batch_no or 0),
    }
