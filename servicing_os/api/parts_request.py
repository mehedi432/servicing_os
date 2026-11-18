
import frappe
from frappe.utils import nowdate, flt

from servicing_os.api.site_company_706 import current_company, validate_job_shop
WAREHOUSE = "Spare Parts - AMCL"
ITEM_GROUP = "Computer Spare Parts"

MANAGER_ROLES = {"System Manager", "Stock Manager"}
TECHNICIAN_ROLE = "Service Technician"


def is_manager():
    user = frappe.session.user
    return (
        user == "Administrator"
        or bool(
            MANAGER_ROLES.intersection(
                frappe.get_roles(user)
            )
        )
    )


def check_job_access(job_name, write=False):
    if not job_name:
        frappe.throw("Service Job is required.")

    if not frappe.db.exists("Service Job", job_name):
        frappe.throw("Service Job not found.")

    job = frappe.get_doc("Service Job", job_name)

    validate_job_shop(job)

    if is_manager():
        return job

    user = frappe.session.user

    if TECHNICIAN_ROLE not in frappe.get_roles(user):
        frappe.throw(
            "Service Technician role required.",
            frappe.PermissionError,
        )

    if job.technician != user:
        frappe.throw(
            "This Service Job is not assigned to you.",
            frappe.PermissionError,
        )

    if write and job.status in (
        "Delivered",
        "Cancelled",
    ):
        frappe.throw(
            "Cannot request parts for a closed job."
        )

    return job


def check_item(item_code):
    if not frappe.db.exists("Item", item_code):
        frappe.throw("Item not found.")

    item = frappe.get_doc("Item", item_code)

    if item.disabled:
        frappe.throw("Item is disabled.")

    if not item.is_stock_item:
        frappe.throw("Item must be a stock item.")

    if not item.is_sales_item:
        frappe.throw("Part must be enabled as a Sales Item.")

    return item


def setup():
    """Installation only; run using bench execute."""

    if not frappe.db.exists("Company", current_company()):
        frappe.throw("Company missing: " + current_company())

    if not frappe.db.exists("Warehouse", WAREHOUSE):
        frappe.throw("Warehouse missing: " + WAREHOUSE)

    wh = frappe.get_doc("Warehouse", WAREHOUSE)

    if wh.company != current_company() or wh.is_group or wh.disabled:
        frappe.throw("Invalid Spare Parts warehouse.")

    if not frappe.db.exists("Item Group", ITEM_GROUP):
        frappe.throw(
            "Computer Spare Parts Item Group missing."
        )

    fieldname = "custom_service_job"

    existing = frappe.get_meta(
        "Material Request"
    ).get_field(fieldname)

    if existing:
        if (
            existing.fieldtype != "Link"
            or existing.options != "Service Job"
        ):
            frappe.throw(
                "Existing custom_service_job field "
                "has incompatible configuration."
            )
        return {
            "success": True,
            "field": fieldname,
            "action": "already_exists",
        }

    frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Material Request",
        "fieldname": fieldname,
        "label": "Service Job",
        "fieldtype": "Link",
        "options": "Service Job",
        "insert_after": "material_request_type",
        "in_list_view": 1,
        "in_standard_filter": 1,
        "no_copy": 1,
    }).insert(ignore_permissions=True)

    frappe.clear_cache(doctype="Material Request")

    return {
        "success": True,
        "field": fieldname,
        "action": "created",
        "stock_transactions": 0,
    }


@frappe.whitelist()
def create_parts_request(
    job_name,
    item_code,
    qty,
    remarks=None,
):
    """Create a draft ERPNext Material Request."""

    check_job_access(job_name, write=True)
    item = check_item(item_code)

    try:
        quantity = flt(qty)
    except Exception:
        frappe.throw("Invalid quantity.")

    if quantity <= 0:
        frappe.throw("Quantity must be greater than zero.")

    if quantity > 100000:
        frappe.throw("Quantity exceeds allowed limit.")

    if not frappe.get_meta(
        "Material Request"
    ).has_field("custom_service_job"):
        frappe.throw(
            "Setup not installed. Run setup first."
        )

    warehouse = frappe.get_doc(
        "Warehouse", WAREHOUSE
    )

    if (
        warehouse.company != current_company()
        or warehouse.disabled
        or warehouse.is_group
    ):
        frappe.throw("Spare Parts warehouse unavailable.")

    user = frappe.session.user

    mr = frappe.get_doc({
        "doctype": "Material Request",
        "material_request_type": "Material Issue",
        "company": current_company(),
        "transaction_date": nowdate(),
        "schedule_date": nowdate(),
        "custom_service_job": job_name,
        "set_warehouse": WAREHOUSE,
        "remarks": (
            "Service Job: " + job_name
            + "\nRequested by: " + user
            + ("\n" + str(remarks)[:500] if remarks else "")
        ),
        "items": [
            {
                "item_code": item.item_code,
                "qty": quantity,
                "uom": item.stock_uom,
                "schedule_date": nowdate(),
                "warehouse": WAREHOUSE,
            }
        ],
    })

    # Technician permissions are enforced explicitly
    # above, rather than giving every technician
    # unrestricted Material Request access.
    mr.insert(ignore_permissions=True)

    return {
        "success": True,
        "material_request": mr.name,
        "service_job": job_name,
        "item_code": item_code,
        "qty": quantity,
        "status": "Draft",
        "stock_deducted": False,
    }


@frappe.whitelist()
def list_parts_requests(job_name=None):
    """List requests within the user's allowed jobs."""

    filters = {
        "material_request_type": "Material Issue",
        "company": current_company(),
        "custom_service_job": ["is", "set"],
    }

    if job_name:
        check_job_access(job_name)
        filters["custom_service_job"] = job_name

    elif not is_manager():
        user = frappe.session.user

        if TECHNICIAN_ROLE not in frappe.get_roles(user):
            frappe.throw(
                "Not permitted.",
                frappe.PermissionError,
            )

        assigned_jobs = frappe.get_all(
            "Service Job",
            filters={"technician": user},
            pluck="name",
            limit_page_length=1000,
        )

        if not assigned_jobs:
            return {"requests": []}

        filters["custom_service_job"] = [
            "in", assigned_jobs
        ]

    requests = frappe.get_all(
        "Material Request",
        filters=filters,
        fields=[
            "name",
            "custom_service_job",
            "material_request_type",
            "transaction_date",
            "status",
            "docstatus",
            "owner",
        ],
        order_by="creation desc",
        limit_page_length=200,
    )

    return {"requests": requests}


@frappe.whitelist()
def approve_parts_request(material_request):
    """Manager submits an approved Material Request."""

    if not is_manager():
        frappe.throw(
            "Manager permission required.",
            frappe.PermissionError,
        )

    mr = frappe.get_doc(
        "Material Request",
        material_request,
    )

    if mr.company != current_company():
        frappe.throw("Incorrect Company.")

    if mr.material_request_type != "Material Issue":
        frappe.throw("Incorrect request purpose.")

    if not mr.custom_service_job:
        frappe.throw("Service Job reference missing.")

    check_job_access(mr.custom_service_job)

    if mr.docstatus != 0:
        frappe.throw(
            "Only Draft requests can be approved."
        )

    for row in mr.items:
        check_item(row.item_code)

        if flt(row.qty) <= 0:
            frappe.throw("Invalid item quantity.")

        if row.warehouse != WAREHOUSE:
            frappe.throw(
                "Unexpected warehouse in item row."
            )

    # Standard ERPNext submission and validations.
    # This DOES NOT create a Stock Entry.
    mr.flags.ignore_permissions = True
    mr.submit()

    return {
        "success": True,
        "material_request": mr.name,
        "docstatus": mr.docstatus,
        "status": mr.status,
        "stock_deducted": False,
    }



# SERVICING_MULTI_PARTS_615C3
@frappe.whitelist()
def create_multi_parts_request(job_name, items, remarks=None):
    """Create ONE ERPNext Material Request with any positive number of item rows."""
    import json
    from decimal import Decimal, InvalidOperation

    check_job_access(job_name, write=True)
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except (ValueError, TypeError):
            frappe.throw("Items must be a valid JSON array.")
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        frappe.throw("Enter between 1 and 100 part lines per request.")
    if not frappe.get_meta("Material Request").has_field("custom_service_job"):
        frappe.throw("Material Request Service Job field is missing.")
    wh = frappe.get_doc("Warehouse", WAREHOUSE)
    if wh.company != current_company() or wh.disabled or wh.is_group:
        frappe.throw("Spare Parts warehouse is unavailable.")

    mr_lines = []
    seen = set()
    for idx, line in enumerate(items, 1):
        if not isinstance(line, dict):
            frappe.throw("Invalid part line %s." % idx)
        item_code = str(line.get("item_code") or "").strip()
        if not item_code:
            frappe.throw("Choose an Item for line %s." % idx)
        if item_code in seen:
            frappe.throw("Duplicate Item: %s. Increase its quantity instead." % item_code)
        seen.add(item_code)
        item = check_item(item_code)
        try:
            qty = Decimal(str(line.get("qty")))
        except (InvalidOperation, ValueError, TypeError):
            frappe.throw("Invalid quantity for %s." % item_code)
        if not qty.is_finite() or qty <= 0 or qty > 100000:
            frappe.throw("Quantity must be positive and valid for %s." % item_code)
        mr_lines.append({
            "item_code": item.item_code,
            "qty": float(qty),
            "uom": item.stock_uom,
            "schedule_date": nowdate(),
            "warehouse": WAREHOUSE,
        })

    mr = frappe.get_doc({
        "doctype": "Material Request",
        "material_request_type": "Material Issue",
        "company": current_company(),
        "transaction_date": nowdate(),
        "schedule_date": nowdate(),
        "custom_service_job": job_name,
        "set_warehouse": WAREHOUSE,
        "remarks": "Service Job: " + job_name + "\nRequested by: "
                   + frappe.session.user
                   + ("\n" + str(remarks)[:500] if remarks else ""),
        "items": mr_lines,
    })
    mr.insert(ignore_permissions=True)
    return {
        "success": True,
        "material_request": mr.name,
        "service_job": job_name,
        "line_count": len(mr_lines),
        "status": "Draft",
        "stock_deducted": False,
    }
