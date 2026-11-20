"""Active company/shop resolver for SERVICING OS.

Resolves from the current Frappe site at request time, rather than caching a
hard-coded company at Python import time. Do not weaken shop ownership checks.
"""
import frappe


def site_shop_context():
    request = getattr(getattr(frappe, "local", None), "request", None)
    cached = getattr(frappe.local, "sos_shop_context", None) if request is not None else None
    if cached:
        return cached.copy()

    company_setting = str(frappe.conf.get("servicing_os_company") or "").strip()
    shop_setting = str(frappe.conf.get("servicing_os_shop") or "").strip()

    filters = {"is_active": 1}
    if company_setting:
        filters["company"] = company_setting
    if shop_setting:
        filters["name"] = shop_setting

    shops = frappe.get_all(
        "Servicing Shop",
        filters=filters,
        fields=["name", "company"],
        limit_page_length=2,
    )
    if len(shops) != 1:
        frappe.throw(
            "Expected exactly one active Servicing Shop for this site. "
            "Check site_config.json settings servicing_os_company and "
            "servicing_os_shop.",
            frappe.ValidationError,
        )

    shop = shops[0]
    company = str(shop.company or "").strip()
    if not company or not frappe.db.exists("Company", company):
        frappe.throw("Active Servicing Shop has no valid ERPNext Company.")
    if company_setting and company_setting != company:
        frappe.throw("Configured company does not match the active Servicing Shop.")
    context = {"company": company, "shop": shop.name}
    if request is not None:
        frappe.local.sos_shop_context = context
    return context.copy()


def current_company():
    return site_shop_context()["company"]


def validate_job_shop(job):
    context = site_shop_context()
    if not job.get("shop") or job.get("shop") != context["shop"]:
        frappe.throw(
            "Service Job does not belong to the active Servicing Shop.",
            frappe.PermissionError,
        )
    return context


WAREHOUSE_FIELDS = {
    "retail_warehouse": "Stores",
    "spare_parts_warehouse": "Spare Parts",
    "used_laptop_warehouse": "Used Laptops",
}


def shop_warehouses():
    context = site_shop_context()
    shop = frappe.get_cached_doc("Servicing Shop", context["shop"])
    return {field: shop.get(field) for field in WAREHOUSE_FIELDS}


def retail_warehouse():
    return shop_warehouses()["retail_warehouse"]


def spare_parts_warehouse():
    return shop_warehouses()["spare_parts_warehouse"]


def used_laptop_warehouse():
    return shop_warehouses()["used_laptop_warehouse"]


def current_currency(company=None):
    return frappe.get_cached_value("Company", company or current_company(), "default_currency")


def price_list_for(company, direction):
    currency = current_currency(company)
    label = f"Standard {direction.title()}"
    candidates = (label, f"Servicing OS {direction.title()} - {currency}")
    filters = {"currency": currency, "enabled": 1, direction: 1}
    for name in candidates:
        if frappe.db.exists("Price List", {**filters, "name": name}):
            return name
    options = frappe.get_all("Price List", filters=filters, pluck="name", order_by="name asc",
                             limit_page_length=1)
    return options[0] if options else None


def selling_price_list():
    return price_list_for(current_company(), "selling")


def cash_account(company=None):
    company = company or current_company()
    mode = frappe.db.get_value("Mode of Payment", "Cash", ["enabled", "type"], as_dict=True)
    if not mode or not mode.enabled or mode.type != "Cash":
        return None
    return frappe.db.get_value("Mode of Payment Account", {
        "parent": "Cash", "parenttype": "Mode of Payment", "company": company,
    }, "default_account")
