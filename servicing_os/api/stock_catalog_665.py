"""SERVICING OS 6.65 — browsable in-stock catalog for shop sales.

Read-only endpoint; no inventory, invoices or pricing records are modified.
The configured active shop / warehouse and normal Item permissions are checked.
"""
import frappe
from frappe.utils import flt, cint
from servicing_os.api.counter_selling_price_660 import _pricing_list, _item_price
from servicing_os.api.counter_invoice_654 import shop_config


@frappe.whitelist(methods=['GET'])
def get_available_stock(cursor=0):
    shop = shop_config()  # Login, authorized shop, active company and warehouses
    if not frappe.has_permission('Item', 'read'):
        frappe.throw('Item read permission required.', frappe.PermissionError)
    if not (frappe.has_permission('Sales Invoice', 'create') or frappe.has_permission('POS Invoice', 'create')):
        frappe.throw('Sales-create permission required.', frappe.PermissionError)
    try:
        cursor = max(0, min(100000, int(cursor)))
    except (TypeError, ValueError):
        cursor = 0
    warehouse = shop.retail_warehouse
    price_list, currency = _pricing_list(shop)
    # Only retrieve stock for the explicitly authorized, validated shop warehouse.
    # Bin has a separate ACL; use its quantities only after checking shop and Item access.
    scanned = 0
    result = []
    offset = cursor
    max_scan = 800
    while len(result) < 20 and scanned < max_scan:
        rows = frappe.get_all('Bin', filters={'warehouse': warehouse, 'actual_qty': ['>', 0]},
                              fields=['item_code', 'actual_qty', 'reserved_qty'], order_by='modified desc, name desc',
                              start=offset, limit_page_length=80)
        if not rows:
            break
        codes = [x.item_code for x in rows]
        allowed = frappe.get_list('Item', filters={'name': ['in', codes], 'disabled': 0,
                                                   'is_sales_item': 1},
                                  fields=['name', 'item_name', 'stock_uom', 'is_stock_item',
                                          'has_serial_no', 'has_batch_no', 'has_variants'],
                                  limit_page_length=80)
        item_map = {x.name: x for x in allowed}
        for r in rows:
            offset += 1
            scanned += 1
            item = item_map.get(r.item_code)
            available = flt(r.actual_qty) - flt(r.reserved_qty)
            if not item or not cint(item.is_stock_item) or cint(item.has_variants) or available <= 0:
                continue
            price = _item_price(item.name, price_list, currency, item.stock_uom, shop.company)
            result.append({
                'name': item.name, 'item_code': item.name,
                'item_name': item.item_name or item.name,
                'uom': item.stock_uom, 'stock_uom': item.stock_uom,
                'stock_qty': float(available), 'ledger_qty': float(r.actual_qty),
                'list_price': price['rate'] if price else None, 'price_list': price_list,
                'is_stock_item': 1, 'has_serial_no': bool(cint(item.has_serial_no)),
                'has_batch_no': bool(cint(item.has_batch_no)),
            })
            if len(result) >= 20:
                break
        if len(rows) < 80:
            break
    # There may be non-saleable entries in a later page; a subsequent page can be empty.
    future = frappe.get_all('Bin', filters={'warehouse': warehouse, 'actual_qty': ['>', 0]},
                            fields=['item_code'], start=offset, limit_page_length=1)
    return {'items': result, 'has_next': bool(future), 'next_cursor': offset if future else None,
            'warehouse': warehouse, 'count': len(result)}
