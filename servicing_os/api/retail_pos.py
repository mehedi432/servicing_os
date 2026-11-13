"""SERVICING OS: ERPNext native POS discovery and catalog (read-only).

Native ERPNext Point of Sale is the only checkout/stock/accounting authority.
This endpoint does not create or submit an invoice or POS Opening Entry.
"""
import frappe
from frappe.utils import getdate, nowdate, flt, cint

COMPANY = 'AL MODINA COMPUTERS LIMITED'
DEFAULT_WAREHOUSE = 'Stores - AMCL'
DEFAULT_PRICE_LIST = 'Standard Selling'


def _meta_fields(doctype):
    return {d.fieldname for d in frappe.get_meta(doctype).fields} | {'name'}


def _permitted_profiles():
    if not frappe.has_permission('POS Profile', 'read'):
        return [], 'Your account cannot read POS Profiles.'
    allowed = _meta_fields('POS Profile')
    needed = ['name', 'company', 'warehouse', 'selling_price_list', 'currency', 'disabled']
    fields = [f for f in needed if f in allowed]
    filters = {'company': COMPANY}
    if 'disabled' in allowed:
        filters['disabled'] = 0
    result = frappe.get_list('POS Profile', filters=filters, fields=fields,
                             order_by='name asc', limit_page_length=100)
    return [dict(r) for r in result], None


def _price_list_details(name):
    if not name or not frappe.db.exists('Price List', name):
        return None
    allowed = _meta_fields('Price List')
    wanted = ['name', 'currency', 'selling', 'enabled']
    data = frappe.db.get_value('Price List', name, [f for f in wanted if f in allowed],
                               as_dict=True)
    return dict(data) if data else None


def _warehouse_status(name):
    if not name or not frappe.db.exists('Warehouse', name):
        return {'name': name, 'valid': False, 'reason': 'Warehouse does not exist'}
    fields = ['company', 'is_group', 'disabled']
    value = frappe.db.get_value('Warehouse', name, fields, as_dict=True)
    valid = (value.company == COMPANY and not value.is_group and not value.disabled)
    return {'name': name, 'valid': bool(valid),
            'reason': '' if valid else 'Warehouse is not a usable AMCL stock warehouse'}


def _current_list_prices(item_codes, price_list):
    # Display only the list rate; native POS can apply taxes, discounts and
    # pricing rules to produce a DIFFERENT final selling rate.
    if not item_codes or not price_list or not frappe.has_permission('Item Price', 'read'):
        return {}
    allowed = _meta_fields('Item Price')
    wanted = ['name', 'item_code', 'price_list_rate', 'currency', 'uom',
              'valid_from', 'valid_upto', 'selling']
    fields = [f for f in wanted if f in allowed]
    filters = {'item_code': ['in', item_codes], 'price_list': price_list}
    if 'selling' in allowed:
        filters['selling'] = 1
    prices = frappe.get_list('Item Price', filters=filters, fields=fields,
                             order_by='modified desc', limit_page_length=500)
    today = getdate(nowdate())
    found = {}
    for row in prices:
        r = dict(row)
        if r['item_code'] in found:
            continue
        if r.get('valid_from') and getdate(r['valid_from']) > today:
            continue
        if r.get('valid_upto') and getdate(r['valid_upto']) < today:
            continue
        found[r['item_code']] = {
            'rate': flt(r['price_list_rate']),
            'currency': r.get('currency'),
            'uom': r.get('uom'),
            'price_list': price_list,
        }
    return found


@frappe.whitelist(methods=['GET'])
def get_retail_pos_hub(search='', pos_profile=None, limit=60):
    """Read-only retail POS setup and Item catalog.

    Quantities are Stock Ledger/Bin actual quantities, not final POS
    availability (which can also account for open POS session reservations).
    """
    for doctype in ('Item', 'Warehouse'):
        if not frappe.has_permission(doctype, 'read'):
            frappe.throw('Missing read permission: ' + doctype, frappe.PermissionError)

    profiles, profile_warning = _permitted_profiles()
    chosen = None
    requested = (pos_profile or '').strip()
    if requested:
        chosen = next((p for p in profiles if p['name'] == requested), None)
        if not chosen:
            frappe.throw('Selected POS Profile is unavailable to this user.', frappe.PermissionError)
    elif profiles:
        chosen = profiles[0]

    warehouse = (chosen or {}).get('warehouse') or DEFAULT_WAREHOUSE
    selling_list = (chosen or {}).get('selling_price_list') or DEFAULT_PRICE_LIST
    wh = _warehouse_status(warehouse)
    pl = _price_list_details(selling_list)
    warnings = []
    if profile_warning:
        warnings.append(profile_warning)
    if not profiles:
        warnings.append('No accessible AMCL POS Profile. Create and configure one in ERPNext first.')
    if not wh['valid']:
        warnings.append('POS warehouse is not valid: ' + str(wh['reason']))
    if not pl or not cint(pl.get('selling', 0)) or not cint(pl.get('enabled', 1)):
        warnings.append('Selling Price List is missing or inactive: ' + selling_list)
    if pl and pl.get('currency') != 'BDT':
        warnings.append('Selling Price List is not BDT. Displayed prices are not converted.')
    if chosen and not (chosen.get('warehouse') or ''):
        warnings.append('POS Profile has no warehouse; configure the correct stock warehouse in ERPNext.')

    search = (search or '').strip()[:100]
    try:
        limit = max(1, min(100, int(limit)))
    except (TypeError, ValueError):
        limit = 60
    allowed = _meta_fields('Item')
    item_fields = [f for f in ('name', 'item_name', 'item_group', 'stock_uom',
                               'is_stock_item', 'has_serial_no', 'has_batch_no') if f in allowed]
    filters = {'disabled': 0, 'is_sales_item': 1}
    if 'has_variants' in allowed:
        filters['has_variants'] = 0
    query = {'filters': filters, 'fields': item_fields,
             'order_by': 'item_name asc', 'limit_page_length': limit}
    if search:
        pattern = '%' + search.replace('%', r'\%').replace('_', r'\_') + '%'
        query['or_filters'] = [
            ['Item', 'name', 'like', pattern],
            ['Item', 'item_name', 'like', pattern],
        ]
    items = frappe.get_list('Item', **query)
    item_codes = [row.name for row in items]
    price_map = _current_list_prices(item_codes, selling_list)
    listed = []
    for row in items:
        r = dict(row)
        qty = None
        if cint(r.get('is_stock_item')) and wh['valid']:
            qty = flt(frappe.db.get_value('Bin', {
                'item_code': r['name'], 'warehouse': warehouse
            }, 'actual_qty') or 0)
        listed.append({
            'item_code': r['name'], 'item_name': r.get('item_name') or r['name'],
            'item_group': r.get('item_group'), 'uom': r.get('stock_uom'),
            'is_stock_item': bool(cint(r.get('is_stock_item'))),
            'serial_tracking': bool(cint(r.get('has_serial_no'))),
            'batch_tracking': bool(cint(r.get('has_batch_no'))),
            'ledger_qty': qty,
            'list_price': price_map.get(r['name']),
        })

    customer_ready = None
    if frappe.has_permission('Customer', 'read'):
        customer_ready = bool(frappe.get_list('Customer', fields=['name'], limit_page_length=1))
        if not customer_ready:
            warnings.append('No accessible Customer found. Configure a POS walk-in customer.')

    return {
        'company': COMPANY, 'currency': 'BDT', 'warehouse': warehouse,
        'warehouse_status': wh, 'selling_price_list': selling_list,
        'price_list_status': pl, 'pos_profiles': profiles,
        'selected_profile': chosen['name'] if chosen else None,
        'customer_available': customer_ready,
        'items': listed, 'items_returned': len(listed),
        'warnings': warnings,
        'native_pos_url': '/app/point-of-sale',
        'basis': {
            'prices': 'Reference Item Price list rates only. ERPNext POS computes final taxes, discounts and pricing rules.',
            'stock': 'Ledger quantity from Bin, not net available-to-sell after open POS reservations.',
            'posting': 'No stock, invoice, GL or payment records are posted from this screen.',
            'session': 'Opening/closing POS sessions and checkout are managed by ERPNext POS.',
        },
    }
