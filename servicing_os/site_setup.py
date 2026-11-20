"""Provision SERVICING OS masters on a configured ERPNext site."""

import frappe

from servicing_os.api.site_company_706 import WAREHOUSE_FIELDS, cash_account, price_list_for
from servicing_os.revenue_streams import setup_income_accounts


def _resolve(company):
    configured = frappe.conf.get("servicing_os_company")
    shop_name = frappe.conf.get("servicing_os_shop")
    if configured and company and configured != company:
        frappe.throw("Company differs from servicing_os_company in site_config.json.")
    company = company or configured
    filters = {"is_active": 1}
    if shop_name:
        filters["name"] = shop_name
    if company:
        filters["company"] = company
    shops = frappe.get_all("Servicing Shop", filters=filters, fields=["name", "company"], limit_page_length=2)
    if len(shops) > 1:
        frappe.throw("Select one active shop using servicing_os_shop in site_config.json.")
    if shops:
        return shops[0].company, shops[0].name
    if shop_name:
        frappe.throw("servicing_os_shop must identify an active Servicing Shop for the selected Company.")
    if not company:
        companies = frappe.get_all("Company", pluck="name", limit_page_length=2)
        if len(companies) != 1:
            frappe.throw("Finish ERPNext Company setup, then rerun the installer. For a multi-company site, pass --company.")
        company = companies[0]
    return company, None


def _warehouse(name, company):
    row = frappe.db.get_value("Warehouse", name, ["company", "disabled", "is_group"], as_dict=True)
    if not row or row.company != company or row.disabled or row.is_group:
        frappe.throw(f"Select an active leaf Warehouse for {company} on Servicing Shop. Current value: {name}.")


def _shop(company, existing):
    if existing:
        shop = frappe.get_doc("Servicing Shop", existing)
    else:
        if frappe.db.exists("Servicing Shop", company.name):
            frappe.throw(f"A Servicing Shop named {company.name} already exists. Select or activate it before setup.")
        shop = frappe.get_doc({"doctype": "Servicing Shop", "shop_name": company.name,
                               "company": company.name, "is_active": 1})
    changed = False
    if not shop.get("currency"):
        shop.currency = company.default_currency
        changed = True
    for field, base in WAREHOUSE_FIELDS.items():
        name = shop.get(field)
        if not name:
            name = f"{base} - {company.abbr}"
            if not frappe.db.exists("Warehouse", name):
                parents = frappe.get_all("Warehouse", filters={
                    "company": company.name, "is_group": 1, "disabled": 0,
                    "parent_warehouse": ["is", "not set"],
                }, pluck="name", limit_page_length=2)
                if len(parents) != 1:
                    frappe.throw(f"Configure an active root Warehouse for {company.name} in ERPNext.")
                warehouse = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": base,
                                            "company": company.name, "parent_warehouse": parents[0]})
                warehouse.insert()
                name = warehouse.name
            shop.set(field, name)
            changed = True
        _warehouse(name, company.name)
    if changed:
        shop.save()
    return shop


def _catalog(company, income):
    groups = ("Used Laptops", "Computer Repair Services")
    for group in groups:
        record = frappe.db.get_value("Item Group", group, ["name", "is_group"], as_dict=True)
        if record:
            if record.is_group:
                frappe.throw(f"{group} must be a leaf Item Group.")
            continue
        root = frappe.get_all("Item Group", filters={"is_group": 1, "parent_item_group": ["is", "not set"]},
                              pluck="name", limit_page_length=2)
        if len(root) != 1:
            frappe.throw("Configure the ERPNext Item Group root before preparing the catalog.")
        frappe.get_doc({"doctype": "Item Group", "item_group_name": group,
                        "parent_item_group": root[0]}).insert()
    code = "AMCL-REPAIR-LABOR"
    if frappe.db.exists("Item", code):
        item = frappe.get_doc("Item", code)
        if item.disabled or item.is_stock_item or not item.is_sales_item:
            frappe.throw(f"{code} must be an active non-stock sales item for repair labor.")
        return item.name
    uom = next((name for name in ("Nos", "Unit") if frappe.db.exists("UOM", name)), None)
    if not uom:
        frappe.throw("Configure a Nos or Unit UOM in ERPNext.")
    item = frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": "Computer Repair Labor",
                           "item_group": "Computer Repair Services", "stock_uom": uom,
                           "is_stock_item": 0, "is_sales_item": 1, "is_purchase_item": 0,
                           "item_defaults": [{"company": company.name, "income_account": income}]})
    item.insert()
    return item.name


def _price_lists(company):
    lists = {}
    for direction in ("buying", "selling"):
        name = price_list_for(company.name, direction)
        if not name:
            name = f"Servicing OS {direction.title()} - {company.default_currency}"
            if frappe.db.exists("Price List", name):
                frappe.throw(f"Enable {name} and check its currency and {direction} setting.")
            doc = frappe.get_doc({"doctype": "Price List", "price_list_name": name,
                                  "enabled": 1, direction: 1, "currency": company.default_currency})
            doc.insert()
            name = doc.name
        lists[direction] = name
    return lists


def _payment(company):
    filters = {"company": company.name, "account_type": "Cash", "is_group": 0,
               "disabled": 0, "account_currency": company.default_currency}
    mode = frappe.get_doc("Mode of Payment", "Cash") if frappe.db.exists("Mode of Payment", "Cash") else None
    if mode and (not mode.enabled or mode.type != "Cash"):
        frappe.throw("Enable ERPNext's Cash Mode of Payment and set its type to Cash.")
    account = cash_account(company.name)
    if account:
        if not frappe.db.exists("Account", {**filters, "name": account}):
            frappe.throw(f"Review the Cash Mode of Payment ledger for {company.name}.")
        return account
    account = company.get("default_cash_account")
    if not account or not frappe.db.exists("Account", {**filters, "name": account}):
        account = frappe.db.exists("Account", {**filters, "name": f"Cash - {company.abbr}"})
    if not account:
        candidates = frappe.get_all("Account", filters=filters, pluck="name", limit_page_length=2)
        if len(candidates) != 1:
            frappe.throw(f"Select the Cash ledger for {company.name} on ERPNext Mode of Payment → Cash.")
        account = candidates[0]
    if not mode:
        mode = frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": "Cash",
                               "type": "Cash", "enabled": 1})
    row = next((row for row in mode.accounts if row.company == company.name), None)
    if row:
        row.default_account = account
    else:
        mode.append("accounts", {"company": company.name, "default_account": account})
    mode.save()
    return account


def prepare(company=None):
    """Set up application masters after the ERPNext Company wizard or a site restore."""
    frappe.only_for("System Manager")
    name, existing = _resolve(company)
    if not frappe.db.exists("Company", name):
        frappe.throw(f"ERPNext Company {name} has not been configured on this site.")
    frappe.db.sql("SELECT name FROM `tabCompany` WHERE name = %s FOR UPDATE", (name,))
    name, existing = _resolve(company or name)
    company = frappe.get_doc("Company", name)
    company.check_permission("write")
    if not company.abbr or not company.default_currency or not company.default_receivable_account:
        frappe.throw(f"Complete ERPNext company and chart of accounts setup for {name}.")
    shop = _shop(company, existing)
    accounts = setup_income_accounts(company=name)["accounts"]
    catalog = _catalog(company, accounts["Servicing"])
    price_lists = _price_lists(company)
    payment = _payment(company)
    if not frappe.db.exists("Role", "Service Technician"):
        frappe.get_doc({"doctype": "Role", "role_name": "Service Technician", "desk_access": 1}).insert()
    return {"shop": shop.name, "company": name, "currency": company.default_currency,
            "warehouses": {key: shop.get(key) for key in WAREHOUSE_FIELDS},
            "income_accounts": accounts, "price_lists": price_lists, "cash_account": payment,
            "labor_item": catalog, "stock_catalog_items": frappe.db.count("Item", {"disabled": 0, "is_stock_item": 1})}
