import frappe

COMPANY = "AL MODINA COMPUTERS LIMITED"
WAREHOUSE = "Spare Parts - AMCL"
INCOME_ACCOUNT = "Service - AMCL"

GROUPS = [
    "Computer Spare Parts",
    "Computer Repair Services",
]

SERVICE_ITEM = "AMCL-REPAIR-LABOR"


def install():
    created = []
    existing = []

    # Preflight checks.
    if not frappe.db.exists("Company", COMPANY):
        frappe.throw("Company not found: " + COMPANY)

    if not frappe.db.exists("Warehouse", WAREHOUSE):
        frappe.throw("Spare Parts warehouse not found.")

    if frappe.db.get_value("Warehouse", WAREHOUSE, "company") != COMPANY:
        frappe.throw("Warehouse belongs to a different company.")

    if frappe.db.get_value("Warehouse", WAREHOUSE, "is_group"):
        frappe.throw("Spare Parts warehouse cannot be a group.")

    if not frappe.db.exists("Account", INCOME_ACCOUNT):
        frappe.throw("Repair income account not found.")

    account = frappe.db.get_value(
        "Account",
        INCOME_ACCOUNT,
        ["company", "root_type", "is_group"],
        as_dict=True,
    )

    if (
        account.company != COMPANY
        or account.root_type != "Income"
        or account.is_group
    ):
        frappe.throw("Invalid repair income account.")

    if not frappe.db.exists("Item Group", "All Item Groups"):
        frappe.throw("All Item Groups root not found.")

    uom = next(
        (
            name for name in ("Nos", "Unit")
            if frappe.db.exists("UOM", name)
        ),
        None,
    )

    if not uom:
        frappe.throw(
            "Neither Nos nor Unit UOM exists. "
            "Configure a UOM before continuing."
        )

    # Validate existing records without changing them.
    for group_name in GROUPS:
        if frappe.db.exists("Item Group", group_name):
            if frappe.db.get_value(
                "Item Group", group_name, "is_group"
            ):
                frappe.throw(
                    group_name + " exists as a parent group. "
                    "Expected a leaf Item Group."
                )

    if frappe.db.exists("Item", SERVICE_ITEM):
        item = frappe.get_doc("Item", SERVICE_ITEM)

        if item.is_stock_item:
            frappe.throw(
                SERVICE_ITEM + " already exists as a stock item."
            )

        if item.item_group != "Computer Repair Services":
            frappe.throw(
                SERVICE_ITEM + " has an unexpected Item Group."
            )

        if item.disabled:
            frappe.throw(
                SERVICE_ITEM + " exists but is disabled."
            )

    # Create Item Groups only if absent.
    for group_name in GROUPS:
        if frappe.db.exists("Item Group", group_name):
            existing.append("Item Group: " + group_name)
            continue

        group = frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": group_name,
            "parent_item_group": "All Item Groups",
            "is_group": 0,
        })

        group.insert(ignore_permissions=True)
        created.append("Item Group: " + group_name)

    # Create a non-stock service item.
    if frappe.db.exists("Item", SERVICE_ITEM):
        existing.append("Item: " + SERVICE_ITEM)
    else:
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": SERVICE_ITEM,
            "item_name": "Computer Repair Labor",
            "description": "Computer diagnosis and repair labor charges",
            "item_group": "Computer Repair Services",
            "stock_uom": uom,
            "is_stock_item": 0,
            "is_sales_item": 1,
            "is_purchase_item": 0,
            "disabled": 0,
            "item_defaults": [
                {
                    "company": COMPANY,
                    "income_account": INCOME_ACCOUNT,
                }
            ],
        })

        item.insert(ignore_permissions=True)
        created.append("Item: " + SERVICE_ITEM)

    return {
        "success": True,
        "company": COMPANY,
        "warehouse": WAREHOUSE,
        "created": created,
        "already_existing": existing,
        "stock_transactions_created": 0,
        "sales_invoices_created": 0,
    }
