"""SERVICING OS 6.60 — permission-checked selling price lookup.

Read-only: obtains the applicable Item Price in the configured selling Price List.
Never uses valuation, purchase price, or a made-up zero fallback.
"""

import frappe
from frappe.utils import getdate, nowdate


def _pricing_list(shop):
    company_currency = frappe.db.get_value('Company', shop.company, 'default_currency')
    if not company_currency:
        frappe.throw('Shop company has no default currency.')

    custom_price_list = None
    shop_meta = frappe.get_meta('Servicing Shop')
    if shop_meta.has_field('selling_price_list'):
        custom_price_list = frappe.db.get_value('Servicing Shop', shop.name, 'selling_price_list')

    price_list = (
        custom_price_list
        or frappe.db.get_single_value('Selling Settings', 'selling_price_list')
        or 'Standard Selling'
    )
    details = frappe.db.get_value(
        'Price List', price_list, ['enabled', 'selling', 'currency'], as_dict=True
    )
    if not details or not details.enabled or not details.selling:
        frappe.throw('Configure an enabled selling Price List in Selling Settings / Servicing Shop.')
    if details.currency != company_currency:
        frappe.throw(
            'Selling Price List ' + price_list + ' is in ' + str(details.currency)
            + ', but the shop uses ' + str(company_currency)
            + '. Configure a selling list in the shop currency.'
        )
    return price_list, company_currency


def _item_price(item_code, price_list, currency, uom, company, customer=None):
    meta = frappe.get_meta('Item Price')
    optional = (
        'uom', 'customer', 'customer_group', 'supplier', 'valid_from',
        'valid_upto', 'batch_no', 'min_qty', 'currency', 'company'
    )
    fields = ['name', 'price_list_rate'] + [x for x in optional if meta.has_field(x)]
    filters = {'item_code': item_code, 'price_list': price_list}
    if meta.has_field('selling'):
        filters['selling'] = 1
    # Item Price is explicitly limited to a validated selling list and sellable item.
    # Read access to the selected item and sales-create permission is checked above.
    prices = frappe.get_all(
        'Item Price', filters=filters, fields=fields,
        order_by='valid_from desc, creation desc' if meta.has_field('valid_from') else 'creation desc',
        limit_page_length=100
    )
    today = getdate(nowdate())
    matched = []
    for row in prices:
        if row.get('valid_from') and getdate(row.valid_from) > today:
            continue
        if row.get('valid_upto') and getdate(row.valid_upto) < today:
            continue
        if row.get('currency') and row.currency != currency:
            continue
        if row.get('uom') and row.uom != uom:
            continue
        if row.get('company') and row.company != company:
            continue
        if row.get('supplier') or row.get('batch_no'):
            continue  # Do not mistake buying or batch-specific prices for general selling prices.
        if row.get('min_qty') and float(row.min_qty) > 1:
            continue
        if row.get('customer') and row.customer != customer:
            continue
        if row.get('customer_group'):
            # No customer-group selection in the counter; use a general rate.
            continue
        try:
            rate = float(row.price_list_rate)
        except (TypeError, ValueError):
            continue
        if rate < 0:
            continue
        matched.append((1 if row.get('customer') else 0, row, rate))
    if not matched:
        return None
    matched.sort(key=lambda x: -x[0])  # Among equal specificity, keep newest valid row.
    _, row, rate = matched[0]
    return {'item_price': row.name, 'rate': rate}


@frappe.whitelist(methods=['GET'])
def get_selling_price(item_code=None, customer=None):
    from servicing_os.api.counter_invoice_654 import shop_config

    shop = shop_config()  # Active shop, company/warehouses, login + shop permission.
    if not (frappe.has_permission('Sales Invoice', 'create') or frappe.has_permission('POS Invoice', 'create')):
        frappe.throw('Sales-create permission required to view counter selling prices.', frappe.PermissionError)

    code = str(item_code or '').strip()
    if not code or len(code) > 140:
        frappe.throw('Select a valid Item Code.')
    if not frappe.has_permission('Item', 'read', code):
        frappe.throw('Item read permission required.', frappe.PermissionError)
    item = frappe.db.get_value('Item', code,
        ['name', 'item_name', 'stock_uom', 'is_sales_item', 'disabled'], as_dict=True)
    if not item or item.disabled or not item.is_sales_item:
        frappe.throw('The selected item is not an active selling item.')

    cust = str(customer or '').strip() or None
    if cust and (not frappe.db.exists('Customer', cust) or not frappe.has_permission('Customer', 'read', cust)):
        frappe.throw('Invalid or inaccessible Customer.', frappe.PermissionError)

    price_list, currency = _pricing_list(shop)
    priced = _item_price(item.name, price_list, currency, item.stock_uom, shop.company, cust)
    return {
        'item_code': item.name,
        'item_name': item.item_name,
        'uom': item.stock_uom,
        'price_list': price_list,
        'currency': currency,
        'found': priced is not None,
        'rate': priced['rate'] if priced else None,
        'item_price': priced['item_price'] if priced else None,
        'message': None if priced else (
            'No current selling price is configured for ' + item.name +
            ' (' + item.stock_uom + ') in ' + price_list +
            '. Create or update an Item Price before this sale.'
        ),
    }
