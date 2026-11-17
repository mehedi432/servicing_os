"""Counter spare-parts fulfillment for approved Service Job Material Requests.

Uses ERPNext v15's native Material Request -> Stock Entry mapper and submit hooks.
No force flags or permission bypasses. All stock effects are explicit and audited.
"""
import frappe
from frappe import _
from frappe.utils import flt


def _read_request(material_request):
    if frappe.session.user == 'Guest':
        frappe.throw(_('Login required'), frappe.PermissionError)
    if not isinstance(material_request, str) or not 0 < len(material_request.strip()) <= 140:
        frappe.throw(_('Invalid Material Request'))
    from servicing_os.api.parts_request import COMPANY, WAREHOUSE, check_job_access
    mr = frappe.get_doc('Material Request', material_request.strip())
    mr.check_permission('read')
    if mr.company != COMPANY or mr.material_request_type != 'Material Issue':
        frappe.throw(_('This is not a repair-parts Material Request'))
    if not mr.get('custom_service_job'):
        frappe.throw(_('Material Request is not linked to a Service Job'))
    job = check_job_access(mr.custom_service_job)
    if job.status in ('Delivered', 'Cancelled', 'Canceled'):
        frappe.throw(_('This Service Job is closed; parts cannot be issued'))
    if mr.set_warehouse != WAREHOUSE:
        frappe.throw(_('Unexpected spare-parts warehouse'))
    return mr


def _stock_entries(name):
    return frappe.db.sql("""SELECT DISTINCT se.name, se.docstatus
        FROM `tabStock Entry` se
        INNER JOIN `tabStock Entry Detail` row ON row.parent=se.name
        WHERE row.material_request=%s AND se.docstatus IN (0,1)
        ORDER BY se.name LIMIT 10""", (name,), as_dict=True)


@frappe.whitelist(methods=['GET'])
def issue_state(material_request):
    """Read-only issue state, restricted to operators who can read this request."""
    mr = _read_request(material_request)
    links = _stock_entries(mr.name)
    return {
        'material_request': mr.name,
        'stock_entries': [dict(name=r.name, submitted=(r.docstatus == 1)) for r in links],
        'issued': any(r.docstatus == 1 for r in links),
        'has_draft': any(r.docstatus == 0 for r in links),
        'can_issue': (mr.docstatus == 1 and not links and _has_stock_permissions()),
    }


def _has_stock_permissions():
    from servicing_os.api.parts_request import is_manager
    return bool(is_manager() and frappe.has_permission('Stock Entry', 'create')
                and frappe.has_permission('Stock Entry', 'submit'))


@frappe.whitelist(methods=['POST'])
def issue_parts(material_request, confirm):
    """One explicit, manager-authorized stock issue from an approved parts request.

    Native ERPNext mapping and submission update Material Request and Stock Ledger;
    duplicate requests, serial/batch Items, and insufficient stock are rejected.
    """
    if not _has_stock_permissions():
        frappe.throw(_('Stock Manager permissions to Create and Submit Stock Entry are required'), frappe.PermissionError)
    if confirm != material_request:
        frappe.throw(_('Confirmation must match the Material Request number'))
    # Row lock serializes two concurrent attempts to fulfill the same request.
    frappe.db.sql('SELECT name FROM `tabMaterial Request` WHERE name=%s FOR UPDATE', (material_request,))
    mr = _read_request(material_request)
    if mr.docstatus != 1:
        frappe.throw(_('Approve this Material Request before issuing stock'))
    existing = _stock_entries(mr.name)
    if existing:
        frappe.throw(_('Stock Entry {0} already references this request. Complete or cancel it instead.').format(existing[0].name))
    from erpnext.stock.doctype.material_request.material_request import make_stock_entry
    stock_entry = make_stock_entry(mr.name)
    from servicing_os.api.parts_request import WAREHOUSE
    if not stock_entry.items:
        frappe.throw(_('No remaining quantity to issue against this request'))
    if stock_entry.purpose != 'Material Issue' or stock_entry.company != mr.company:
        frappe.throw(_('Unexpected Stock Entry mapping; no stock issued'))
    for row in stock_entry.items:
        if row.material_request != mr.name or row.s_warehouse != WAREHOUSE or row.t_warehouse:
            frappe.throw(_('Unexpected warehouse or Material Request reference on Stock Entry'))
        quantity = flt(row.transfer_qty or flt(row.qty) * flt(row.conversion_factor or 1))
        if quantity <= 0:
            frappe.throw(_('Invalid issued quantity for Item {0}').format(row.item_code))
        flags = frappe.db.get_value('Item', row.item_code, ['has_serial_no', 'has_batch_no'], as_dict=True)
        if flags and (flags.has_serial_no or flags.has_batch_no):
            frappe.throw(_('Serialized or batch Item {0} requires detailed selection in ERPNext Stock Entry').format(row.item_code))
        b = frappe.db.get_value('Bin', {'item_code': row.item_code, 'warehouse':WAREHOUSE},
                                ['actual_qty', 'reserved_qty'], as_dict=True)
        available = flt(b.actual_qty) - flt(b.reserved_qty) if b else 0
        if available + 0.000001 < quantity:
            frappe.throw(_('Insufficient stock for {0}: {1} available, {2} required').format(row.item_code, available, quantity))
    stock_entry.insert()     # uses current user's standard ERPNext create permissions
    stock_entry.submit()     # uses current user's standard ERPNext submit permissions
    return {'stock_entry': stock_entry.name, 'docstatus': stock_entry.docstatus,
            'material_request': mr.name, 'stock_deducted': stock_entry.docstatus == 1}
