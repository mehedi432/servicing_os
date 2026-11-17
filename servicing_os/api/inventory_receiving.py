"""SERVICING OS v5.7 — isolated, permission-aware stock receiving / Purchase Material Request.

A Material Request is a procurement plan, NOT a stock receipt. The actions are
separate and cannot create a phantom stock balance or supplier liability.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
import frappe
from frappe.utils import getdate, nowdate, flt
from servicing_os.api import inventory_workspace as inv


def _text(value, label, limit=160):
    value = str(value or '').strip()
    if len(value) > limit:
        frappe.throw('%s is too long (max %s characters)' % (label, limit))
    return value


def _positive(value, label, limit='99999999'):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        frappe.throw('%s must be a positive number' % label)
    if not n.is_finite() or n <= 0 or n > Decimal(limit):
        frappe.throw('%s must be between 0 and %s' % (label, limit))
    return float(n)


def _check_shop(item_code, warehouse, allow_serial=False):
    company = inv._company()
    if not frappe.has_permission('Item', 'read'):
        frappe.throw('Item read permission is required', frappe.PermissionError)
    code = _text(item_code, 'Item code', 140)
    if not code:
        frappe.throw('Select an existing product')
    item = frappe.get_doc('Item', code)
    if not frappe.has_permission('Item', 'read', item):
        frappe.throw('Cannot read this product', frappe.PermissionError)
    if item.disabled or not item.is_stock_item:
        frappe.throw('Product is disabled or not stock tracked')
    warehouse = _text(warehouse, 'Warehouse', 140)
    allowed = {w.name for w in inv._warehouses(company)}
    if warehouse not in allowed:
        frappe.throw('Select an active warehouse in this shop', frappe.PermissionError)
    if (item.has_serial_no or item.has_batch_no) and not allow_serial:
        frappe.throw('Serial/batch products require their dedicated ERPNext receipt workflow')
    return company, item, warehouse


def _can_price_update():
    return all(frappe.has_permission('Item Price', p) for p in ('read', 'create', 'write'))


@frappe.whitelist(methods=['GET'])
def get_receive_access():
    company = inv._company()
    price_lists = inv._price_lists(company)
    return {
        'company': company,
        'currency': price_lists['currency'],
        'can_receive': bool(frappe.has_permission('Stock Entry', 'create') and frappe.has_permission('Stock Entry', 'submit')),
        'can_request': bool(frappe.has_permission('Material Request', 'create')),
        'can_price_update': _can_price_update(),
        'buying_price_list': price_lists['buying'],
        'selling_price_list': price_lists['selling'],
    }


@frappe.whitelist(methods=['GET'])
def search_suppliers(q=''):
    inv._company()
    if not frappe.has_permission('Supplier', 'read'):
        return []
    q = _text(q, 'Supplier search', 100)
    filters = {'disabled': 0}
    kws = {}
    if q:
        pattern = '%' + q.replace('%', r'\%').replace('_', r'\_') + '%'
        kws['or_filters'] = {'name': ['like', pattern], 'supplier_name': ['like', pattern]}
    rows = frappe.get_list('Supplier', filters=filters,
        fields=['name', 'supplier_name'], order_by='modified desc',
        limit_page_length=12, **kws)
    return [{'name': r.name, 'label': r.supplier_name or r.name} for r in rows]


@frappe.whitelist(methods=['POST'])
def receive_stock(item_code=None, warehouse=None, qty=None, buying_rate=None,
                  selling_rate=None, supplier=None, supplier_reference=None,
                  notes=None, update_catalog_prices=0):
    """Submit a DIRECT Material Receipt. Does not create a Purchase Receipt/invoice."""
    company, item, warehouse = _check_shop(item_code, warehouse)
    if not (frappe.has_permission('Stock Entry', 'create') and frappe.has_permission('Stock Entry', 'submit')):
        frappe.throw('Stock Entry create and submit permissions required', frappe.PermissionError)
    quantity = _positive(qty, 'Received quantity', '9999999')
    buy = _positive(buying_rate, 'Actual receipt unit cost')
    sell = None
    if selling_rate is not None and str(selling_rate).strip() != '':
        sell = _positive(selling_rate, 'Selling price')
    supplier = _text(supplier, 'Supplier', 140)
    reference = _text(supplier_reference, 'Reference number', 140)
    notes = _text(notes, 'Receiving remarks', 500)
    if supplier:
        if not frappe.has_permission('Supplier', 'read') or not frappe.db.exists('Supplier', supplier):
            frappe.throw('Select an existing supplier from the suggestions', frappe.PermissionError)
        if frappe.db.get_value('Supplier', supplier, 'disabled'):
            frappe.throw('Selected supplier is disabled')
    update = str(update_catalog_prices).strip().lower() in ('1','true','yes')
    if update:
        if not _can_price_update():
            frappe.throw('Item Price read/create/write permissions are required', frappe.PermissionError)
        lists = inv._price_lists(company)
        if not lists['buying']:
            frappe.throw('Configure an enabled buying Price List first')
        if sell is not None and not lists['selling']:
            frappe.throw('Configure an enabled selling Price List first')
        if sell is not None and lists['buying'] == lists['selling']:
            frappe.throw('Buying and selling Price Lists must be distinct')
    else:
        lists = None
    # Explicitly reference-only: this Stock Entry does not recognize supplier debt.
    remarks = 'SERVICING OS • Direct Material Receipt'
    if supplier:
        remarks += '\nSupplier reference (non-accounting): ' + supplier
    if reference:
        remarks += '\nReference: ' + reference
    if notes:
        remarks += '\n' + notes
    result = inv.post_stock_movement(item_code=item.name, warehouse=warehouse,
        qty=quantity, movement='receive', basic_rate=buy, remarks=remarks)
    if update:
        inv._upsert_price(item.name, lists['buying'], buy, item.stock_uom)
        if sell is not None:
            inv._upsert_price(item.name, lists['selling'], sell, item.stock_uom)
    # If a downstream price write fails, the Frappe request rolls back both changes.
    return {
        'stock_entry': result['stock_entry'], 'item_code': item.name,
        'qty': quantity, 'warehouse': warehouse, 'company': company,
        'catalog_prices_updated': bool(update),
        'note': 'Direct Material Receipt only. No supplier payable or Purchase Receipt created.',
    }


@frappe.whitelist(methods=['POST'])
def create_purchase_request(item_code=None, warehouse=None, qty=None,
                            required_by=None, reason=None):
    """Automatically create a DRAFT Purchase Material Request for one selected Item."""
    company, item, warehouse = _check_shop(item_code, warehouse, allow_serial=True)
    if not frappe.has_permission('Material Request', 'create'):
        frappe.throw('Material Request create permission is required', frappe.PermissionError)
    quantity = _positive(qty, 'Required quantity', '9999999')
    due_raw = _text(required_by, 'Required by', 20)
    try:
        due = getdate(due_raw) if due_raw else getdate(nowdate())
    except Exception:
        frappe.throw('Enter a valid required-by date')
    if due < getdate(nowdate()):
        frappe.throw('Required-by date cannot be in the past')
    if (due - getdate(nowdate())).days > 730:
        frappe.throw('Required-by date is too far in the future')
    reason = _text(reason, 'Reason', 500)
    # Stock Planning only: no Stock Ledger Entry, no Purchase Order, no supplier
    # financial transaction. One selected SKU yields one draft MR.
    request = frappe.get_doc({
        'doctype': 'Material Request',
        'company': company,
        'material_request_type': 'Purchase',
        'transaction_date': nowdate(),
        'schedule_date': str(due),
        'items': [{
            'item_code': item.name,
            'item_name': item.item_name,
            'qty': quantity,
            'uom': item.stock_uom,
            'stock_uom': item.stock_uom,
            'conversion_factor': 1,
            'warehouse': warehouse,
            'schedule_date': str(due),
            'description': item.description or item.item_name,
        }],
    })
    if reason:
        # Frappe v15 Material Request may have custom note/description fields.
        if request.meta.has_field('remarks'):
            request.set('remarks', reason)
        elif request.meta.has_field('description'):
            request.set('description', reason)
    request.insert(ignore_permissions=False)
    return {
        'material_request': request.name,
        'docstatus': request.docstatus,
        'status': 'Draft', 'item_code': item.name,
        'qty': quantity, 'warehouse': warehouse,
        'required_by': str(due), 'stock_changed': False,
    }
