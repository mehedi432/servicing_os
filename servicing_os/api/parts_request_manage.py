import frappe
from frappe.utils import flt

# SERVICING_PARTS_UI_615C4
COMPANY = "AL MODINA COMPUTERS LIMITED"
WAREHOUSE = "Spare Parts - AMCL"
MANAGER_ROLES = {"System Manager", "Stock Manager"}
TECHNICIAN_ROLE = "Service Technician"


def _manager():
    user = frappe.session.user
    return user == "Administrator" or bool(MANAGER_ROLES.intersection(set(frappe.get_roles(user))))


def _access():
    if frappe.session.user == "Guest":
        frappe.throw("Login required.", frappe.PermissionError)
    if not _manager() and TECHNICIAN_ROLE not in frappe.get_roles(frappe.session.user):
        frappe.throw("Service Job access required.", frappe.PermissionError)


def _get_request(name, manager_action=False):
    _access()
    if not name or not frappe.db.exists("Material Request", name):
        frappe.throw("Material Request not found.")
    doc = frappe.get_doc("Material Request", name)
    if (doc.company != COMPANY or doc.material_request_type != "Material Issue"
            or not doc.get("custom_service_job")):
        frappe.throw("This is not a SERVICING OS repair-parts request.", frappe.PermissionError)
    if manager_action and not _manager():
        frappe.throw("Only authorized managers can change or remove requests.", frappe.PermissionError)
    from servicing_os.api.parts_request import check_job_access
    check_job_access(doc.custom_service_job)
    return doc


def _linked_stock_entries(name):
    """Do not alter an MR while active Stock Entry drafts/submissions reference it."""
    rows = frappe.db.sql("""
        SELECT DISTINCT se.name, se.docstatus
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE sed.material_request = %s AND se.docstatus IN (0, 1)
        ORDER BY se.name LIMIT 5
    """, (name,), as_dict=True)
    return rows


def _check_no_stock_links(doc):
    links = _linked_stock_entries(doc.name)
    if links:
        frappe.throw("Request is linked to Stock Entry " + links[0].name
                     + ". Resolve that Stock Entry in ERPNext first.")


def _check_version(doc, expected_modified):
    if not expected_modified or str(doc.modified) != str(expected_modified):
        frappe.throw("This request changed since you opened it. Refresh before editing.")


@frappe.whitelist()
def search_saleable_parts(search=""):
    """Search active saleable stock Items, including those with zero stock."""
    _access()
    search = (search or "").strip()[:100]
    filters = {"disabled": 0, "is_stock_item": 1, "is_sales_item": 1}
    or_filters = None
    if search:
        pattern = "%" + search + "%"
        or_filters = [["Item", "name", "like", pattern],
                      ["Item", "item_name", "like", pattern]]
    items = frappe.get_all("Item", filters=filters, or_filters=or_filters,
                           fields=["name", "item_name", "stock_uom"],
                           order_by="item_name asc", limit_page_length=40)
    codes = [i.name for i in items]
    stock = {}
    if codes:
        for row in frappe.get_all("Bin", filters={"warehouse": WAREHOUSE,
                "item_code": ["in", codes]}, fields=["item_code", "actual_qty", "reserved_qty"]):
            stock[row.item_code] = (flt(row.actual_qty), flt(row.reserved_qty))
    return {"items": [{"item_code": i.name, "item_name": i.item_name,
                        "uom": i.stock_uom,
                        "available_qty": stock.get(i.name, (0, 0))[0] - stock.get(i.name, (0, 0))[1]}
                       for i in items], "warehouse": WAREHOUSE}


@frappe.whitelist()
def manage_permissions():
    _access()
    manager = _manager()
    return {
        "manager": manager,
        "can_edit": bool(manager and frappe.has_permission("Material Request", "write")),
        "can_delete": bool(manager and frappe.has_permission("Material Request", "delete")),
        "can_cancel": bool(manager and frappe.has_permission("Material Request", "cancel")),
    }


@frappe.whitelist()
def request_details(material_request):
    mr = _get_request(material_request)
    return {
        "name": mr.name, "service_job": mr.custom_service_job,
        "docstatus": mr.docstatus, "status": mr.status,
        "modified": str(mr.modified),
        "stock_entry_links": [r.name for r in _linked_stock_entries(mr.name)],
        "items": [{"row_name": row.name, "item_code": row.item_code,
                   "item_name": row.item_name, "qty": row.qty,
                   "uom": row.uom} for row in mr.items],
    }


@frappe.whitelist(methods=["POST"])
def remove_draft_part(material_request, row_name, expected_modified):
    """Remove ONE row from a Draft; preserve native ERPNext validation."""
    mr = _get_request(material_request, manager_action=True)
    mr.check_permission("write")
    _check_version(mr, expected_modified)
    if mr.docstatus != 0:
        frappe.throw("Only a Draft Material Request can be edited.")
    _check_no_stock_links(mr)
    if len(mr.items) < 2:
        frappe.throw("This is the last part. Use Delete Draft instead.")
    row = next((x for x in mr.items if x.name == row_name), None)
    if not row:
        frappe.throw("Selected part row not found. Refresh the request.")
    mr.remove(row)
    mr.save()
    return {"success": True, "material_request": mr.name, "remaining_parts": len(mr.items)}


@frappe.whitelist(methods=["POST"])
def delete_draft_request(material_request, expected_modified):
    """Permanently delete a Draft only with standard delete permission."""
    mr = _get_request(material_request, manager_action=True)
    mr.check_permission("delete")
    _check_version(mr, expected_modified)
    if mr.docstatus != 0:
        frappe.throw("Only Draft requests can be deleted here. Cancel submitted requests instead.")
    _check_no_stock_links(mr)
    frappe.delete_doc("Material Request", mr.name)
    return {"success": True, "deleted": material_request}


@frappe.whitelist(methods=["POST"])
def cancel_submitted_request(material_request, expected_modified):
    """Cancel via ERPNext; block any linked active Stock Entries."""
    mr = _get_request(material_request, manager_action=True)
    mr.check_permission("cancel")
    _check_version(mr, expected_modified)
    if mr.docstatus != 1:
        frappe.throw("Only submitted requests can be cancelled.")
    _check_no_stock_links(mr)
    mr.cancel()
    return {"success": True, "cancelled": mr.name, "status": mr.status}


def healthcheck():
    """Read-only bench check (Administrator context)."""
    return {"api": "SERVICING OS 6.15C.4", "warehouse": WAREHOUSE,
            "matching_items": len(search_saleable_parts().get("items", [])),
            "permissions": manage_permissions(),
            "stock_changed": False}
