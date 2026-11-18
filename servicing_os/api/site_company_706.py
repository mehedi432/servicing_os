"""Active company/shop resolver for SERVICING OS.

Resolves from the current Frappe site at request time, rather than caching a
hard-coded company at Python import time. Do not weaken shop ownership checks.
"""
import frappe


def site_shop_context():
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
    return {"company": company, "shop": shop.name}


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
