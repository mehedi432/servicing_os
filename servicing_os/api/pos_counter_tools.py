"""SERVICING OS — POS preparation, barcode lookup & receipt settings.

Read-only. ERPNext Point of Sale remains authoritative for checkout,
customer charges, stock changes, payments and receipt printing.
"""

import frappe
from frappe.utils import cint
from servicing_os.api.retail_pos import get_retail_pos_hub
from servicing_os.api.site_company_706 import current_company



def _allowed_profile(data):
    name = data.get("selected_profile")
    if not name:
        return None, "No usable POS Profile selected."

    # The existing hub uses a permission-filtered POS Profile list.
    if not any(p.get("name") == name for p in data.get("pos_profiles", [])):
        frappe.throw("POS Profile is not permitted.", frappe.PermissionError)

    profile = frappe.get_doc("POS Profile", name)
    profile.check_permission("read")
    if profile.company != current_company() or cint(profile.get("disabled")):
        frappe.throw("This POS Profile is not active for AMCL.")

    assigned = [row.get("user") for row in (profile.get("applicable_for_users") or []) if row.get("user")]
    current = frappe.session.user
    if assigned and current not in assigned and current != "Administrator":
        return None, "This POS Profile is restricted to other cashiers."
    return profile, None


@frappe.whitelist(methods=["GET"])
def get_pos_setup(pos_profile=None):
    """Return a read-only, cashier-specific POS configuration checklist."""
    hub = get_retail_pos_hub(pos_profile=pos_profile, search="", limit=1)
    profile, profile_error = _allowed_profile(hub)

    checks = []

    def check(label, ok, detail, required=True):
        checks.append({
            "label": label,
            "ok": bool(ok),
            "detail": str(detail or ""),
            "required": bool(required),
        })

    check("POS Profile", bool(profile), profile_error or (profile.name if profile else "Create a POS Profile in ERPNext"))
    wh = hub.get("warehouse_status") or {}
    check("Receiving / selling warehouse", bool(wh.get("valid")), hub.get("warehouse") or "Not configured")
    price_list = hub.get("price_list_status") or {}
    price_ok = bool(price_list) and cint(price_list.get("selling")) and cint(price_list.get("enabled", 1))
    check("Selling price list", price_ok, hub.get("selling_price_list") or "Not configured")

    methods = []
    receipt = {"auto_print": False, "print_format": None, "letter_head": None}
    customer = None
    session_status = "Unknown"
    if profile:
        customer = profile.get("customer")
        methods = [
            {"name": row.get("mode_of_payment"), "default": bool(cint(row.get("default")))}
            for row in (profile.get("payments") or [])
            if row.get("mode_of_payment")
        ]
        receipt = {
            "auto_print": bool(cint(profile.get("print_receipt_on_order_complete"))),
            "print_format": profile.get("print_format"),
            "letter_head": profile.get("letter_head"),
        }
        if frappe.has_permission("POS Opening Entry", "read"):
            meta_fields = {d.fieldname for d in frappe.get_meta("POS Opening Entry").fields}
            filters = {"pos_profile": profile.name, "docstatus": 1}
            if "user" in meta_fields:
                filters["user"] = frappe.session.user
            if "status" in meta_fields:
                filters["status"] = "Open"
            matches = frappe.get_list(
                "POS Opening Entry", filters=filters,
                fields=["name"], limit_page_length=1,
            )
            session_status = "Open" if matches else "No open session found"
        else:
            session_status = "Not available to this user"

    check("Payment modes", bool(methods), ", ".join(m["name"] for m in methods) or "Add payment methods on POS Profile")
    check("Default walk-in customer", bool(customer), customer or "Choose a walk-in customer in POS Profile", required=False)
    check("Receipt printing", receipt["auto_print"],
          "Auto print enabled" if receipt["auto_print"] else "Turn on Print Receipt on Order Complete", required=False)

    return {
        "company": current_company(),
        "currency": "BDT",
        "profile": profile.name if profile else None,
        "warehouse": hub.get("warehouse"),
        "price_list": hub.get("selling_price_list"),
        "customer": customer,
        "payment_modes": methods,
        "receipt": receipt,
        "session": session_status,
        "checks": checks,
        "configuration_ready": all(c["ok"] for c in checks if c["required"]),
        "warnings": hub.get("warnings", []),
        "links": {
            "pos": "/app/point-of-sale",
            "profile": "/app/pos-profile",
            "opening": "/app/pos-opening-entry",
            "closing": "/app/pos-closing-entry",
            "items": "/app/item",
        },
        "note": "Read-only setup check. ERPNext POS handles checkout, tax, final stock checks, payments and printing.",
    }


@frappe.whitelist(methods=["GET"])
def lookup_pos_barcode(barcode, pos_profile=None):
    """Identify an active sales Item by exact barcode or Item Code.

    Barcode scanner input is treated as keyboard text. This endpoint does not
    add an Item to a POS cart or alter inventory.
    """
    if not frappe.has_permission("Item", "read"):
        frappe.throw("Item read permission required.", frappe.PermissionError)
    value = str(barcode or "").strip()
    if not value or len(value) > 128:
        frappe.throw("Enter a barcode or Item Code (up to 128 characters).")

    # Check profile access even for lookup requests; matching profile is
    # resolved again in the existing catalog endpoint below.
    hub = get_retail_pos_hub(search="", pos_profile=pos_profile, limit=1)
    selected, profile_error = _allowed_profile(hub)
    if hub.get("selected_profile") and not selected:
        frappe.throw(profile_error or "POS Profile unavailable.", frappe.PermissionError)

    rows = frappe.get_all(
        "Item Barcode", filters={"barcode": value, "parenttype": "Item"},
        fields=["parent"], limit_page_length=10,
    )
    unique_codes = list(dict.fromkeys(row.parent for row in rows))
    if len(unique_codes) > 1:
        return {"found": False, "reason": "Barcode belongs to multiple Items. Resolve the duplicate in ERPNext."}
    code = unique_codes[0] if unique_codes else value
    if not frappe.db.exists("Item", code):
        return {"found": False, "reason": "No Item matches this barcode or Item Code."}

    item = frappe.get_doc("Item", code)
    item.check_permission("read")
    if cint(item.get("disabled")) or not cint(item.get("is_sales_item")):
        return {"found": False, "reason": "The matching Item is disabled or not sales-enabled."}

    # Reuse the profile-specific price list and ledger presentation from
    # the working Retail POS API, rather than duplicating pricing logic.
    found_in_catalog = get_retail_pos_hub(
        search=code, pos_profile=pos_profile, limit=100,
    )
    result = next((x for x in found_in_catalog.get("items", []) if x["item_code"] == code), None)
    if not result:
        return {"found": False, "reason": "Item is not available in the current catalog search."}
    return {
        "found": True,
        "matched_on": "barcode" if unique_codes else "item_code",
        "item": result,
        "note": "Lookup only. Scan or select the Item again in ERPNext POS during checkout.",
    }
