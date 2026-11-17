"""SERVICING OS Inventory v5.6 — permission-aware Item archive/deletion.

Dedicated endpoint so existing Inventory/PO APIs remain untouched.
Permanent deletion is deliberately conservative: it is denied when stock,
commitments or Stock Ledger Entry history exists. Frappe's native link checks
and Item validation are never bypassed.
"""
import frappe
from frappe.utils import flt


def _require_shop():
    # Reuse the same active shop/company resolution as Inventory.
    from servicing_os.api.inventory_workspace import _company
    return _company()


def _item(code):
    code = str(code or '').strip()
    if not code or len(code) > 140 or not frappe.db.exists('Item', code):
        frappe.throw('Product not found')
    item = frappe.get_doc('Item', code)
    if not item.is_stock_item or item.disabled:
        frappe.throw('Only active stock products can be managed here')
    if not frappe.has_permission('Item', 'read', item):
        frappe.throw('Item read permission required', frappe.PermissionError)
    return item


def _risk(item):
    """Check balances in ALL companies/warehouses, not just filtered Inventory."""
    meta = frappe.get_meta('Bin')
    candidate_fields = ('actual_qty', 'reserved_qty', 'ordered_qty', 'indented_qty',
                        'planned_qty', 'reserved_qty_for_production',
                        'reserved_qty_for_sub_contract', 'stock_value')
    available = [x for x in candidate_fields if meta.has_field(x)]
    rows = frappe.get_all('Bin', filters={'item_code': item.name}, fields=available,
                          limit_page_length=5001) if available else []
    balances = any(abs(flt(row.get(field))) > 0.000001
                   for row in rows for field in available)
    too_many = len(rows) > 5000
    # Even cancelled stock transactions are important historical records.
    stock_history = bool(frappe.db.exists('Stock Ledger Entry', {'item_code': item.name}))
    return {'balances_or_commitments': balances or too_many,
            'stock_history': stock_history,
            'reason': ('This item has stock, stock value, reservations or outstanding quantities. Clear them in ERPNext first.'
                       if balances or too_many else
                       'Stock Ledger history exists. This item cannot be permanently deleted here.'
                       if stock_history else '')}


def _permission(item):
    return {'can_archive': bool(frappe.has_permission('Item', 'write', item)),
            'can_delete': bool(frappe.has_permission('Item', 'delete', item))}


@frappe.whitelist(methods=['GET'])
def get_catalog_permissions():
    _require_shop()
    # Per-document permissions still enforced before every operation.
    return {'can_archive': bool(frappe.has_permission('Item', 'write')),
            'can_delete': bool(frappe.has_permission('Item', 'delete'))}


@frappe.whitelist(methods=['GET'])
def get_removal_options(item_code=None):
    _require_shop()
    item = _item(item_code)
    perms = _permission(item)
    risk = _risk(item)
    return {
        'item_code': item.name,
        'item_name': item.item_name or item.name,
        'can_archive': perms['can_archive'] and not risk['balances_or_commitments'],
        'can_delete': perms['can_delete'] and not risk['balances_or_commitments'] and not risk['stock_history'],
        'has_ledger_history': risk['stock_history'],
        'has_stock_or_commitments': risk['balances_or_commitments'],
        'message': risk['reason'],
        'scope_warning': 'Item is shared across ERPNext companies. Disabling or deleting it affects every company.',
    }


@frappe.whitelist(methods=['POST'])
def retire_product(item_code=None, action=None, confirmation=None):
    _require_shop()
    action = str(action or '').strip().lower()
    if action not in ('archive', 'delete'):
        frappe.throw('Choose Archive or Permanent Delete')
    item = _item(item_code)
    if str(confirmation or '').strip() != item.name:
        frappe.throw('Enter the exact SKU to confirm')
    perms = _permission(item)
    risk = _risk(item)  # Recheck under authenticated POST; the UI is not authoritative.
    if risk['balances_or_commitments']:
        frappe.throw(risk['reason'])
    if action == 'archive':
        if not perms['can_archive']:
            frappe.throw('Item write permission required', frappe.PermissionError)
        item.disabled = 1
        item.save()  # respect hooks, validations, activity logging
        return {'item_code': item.name, 'action': 'archived'}
    if not perms['can_delete']:
        frappe.throw('Item delete permission required', frappe.PermissionError)
    if risk['stock_history']:
        frappe.throw(risk['reason'])
    # Do not force/unlink anything. Native link-integrity checks protect POs,
    # invoices, Item Prices, and every other linked ERPNext document.
    frappe.delete_doc('Item', item.name, force=False, ignore_permissions=False)
    return {'item_code': item.name, 'action': 'deleted'}
