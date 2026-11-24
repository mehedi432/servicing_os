"""Supplier registration and linked addresses for SERVICING OS."""

import frappe

SUPPLIER = "Supplier"
PRIMARY = "supplier_primary_address"
ADDRESS_FIELDS = ("address_line1", "address_line2", "city", "state", "pincode", "country")


def _require(doctype, action):
    if not frappe.has_permission(doctype, ptype=action):
        frappe.throw(f"{doctype} {action} permission is required.", frappe.PermissionError)


def _linked_addresses(name):
    links = frappe.get_all("Dynamic Link", filters={
        "parenttype": "Address", "parentfield": "links", "link_doctype": SUPPLIER, "link_name": name,
    }, pluck="parent")
    if not links:
        return []
    return frappe.get_all("Address", filters={"name": ["in", sorted(set(links))], "disabled": 0}, pluck="name")


def _addresses(name, matched=None):
    names = _linked_addresses(name) if matched is None else matched
    if not names:
        return []
    return frappe.get_list("Address", filters={"name": ["in", names], "disabled": 0},
                           fields=["name", *ADDRESS_FIELDS], limit_page_length=len(names),
                           order_by="is_primary_address desc, modified desc, name asc")


def _primary(name, rows):
    preferred = frappe.db.get_value(SUPPLIER, name, PRIMARY) if frappe.get_meta(SUPPLIER).has_field(PRIMARY) else None
    return next((row for row in rows if row["name"] == preferred), rows[0] if rows else None)


def supplier_address(name):
    """Return the preferred visible address for an already authorized Supplier."""
    if frappe.has_permission("Address", ptype="read"):
        return _primary(name, _addresses(name))
    return None


def _address_payload(values, existing):
    if not isinstance(values, dict):
        frappe.throw("Enter the supplier's street address and city or upazila.")
    data = {field: str(values.get(field, (existing or {}).get(field)) or "").strip() for field in ADDRESS_FIELDS}
    if not data["address_line1"] or not data["city"]:
        frappe.throw("Enter the supplier's street address and city or upazila.")
    if not data["country"]:
        data["country"] = frappe.db.get_single_value("System Settings", "country") or "Bangladesh"
    for field, limit in (("address_line1", 140), ("address_line2", 140), ("city", 140), ("state", 140), ("pincode", 20), ("country", 140)):
        if len(data[field]) > limit:
            frappe.throw(f"{field.replace('_', ' ').capitalize()} must be {limit} characters or fewer.")
    if not frappe.db.exists("Country", data["country"]):
        frappe.throw("Select a valid country for the supplier address.")
    return data


@frappe.whitelist(methods=["GET"])
def get_supplier_form(name=None):
    if not name:
        _require(SUPPLIER, "create")
        return {"address": {}, "can_edit_address": bool(frappe.has_permission("Address", ptype="create"))}
    supplier = frappe.get_doc(SUPPLIER, name)
    supplier.check_permission("read")
    supplier.check_permission("write")
    names = _linked_addresses(name)
    visible = _primary(name, _addresses(name, names)) if frappe.has_permission("Address", ptype="read") else None
    writable = (frappe.has_permission("Address", ptype="write", doc=visible["name"]) if visible
                else not names and frappe.has_permission("Address", ptype="create"))
    return {"address": visible or {}, "can_edit_address": bool(writable)}


@frappe.whitelist(methods=["POST"])
def save_supplier(data):
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if not isinstance(data, dict):
        frappe.throw("Supplier details are required.")
    name = str(data.get("name") or "").strip()
    action = "write" if name else "create"
    _require(SUPPLIER, action)
    supplier_name = " ".join(str(data.get("supplier_name") or "").split())
    group = str(data.get("supplier_group") or "").strip()
    kind = str(data.get("supplier_type") or "Company").strip()
    if not 2 <= len(supplier_name) <= 140:
        frappe.throw("Enter a supplier name of 2–140 characters.")
    if not frappe.db.exists("Supplier Group", {"name": group, "is_group": 0}):
        frappe.throw("Select a valid Supplier Group.")
    if name:
        supplier = frappe.get_doc(SUPPLIER, name)
        supplier.check_permission("read")
        supplier.check_permission("write")
    else:
        if frappe.db.exists(SUPPLIER, {"supplier_name": supplier_name}):
            frappe.throw("This supplier already exists. Select the existing record.")
        supplier = frappe.new_doc(SUPPLIER)
    if kind not in ("Company", "Individual") and (not name or supplier.supplier_type != kind):
        frappe.throw("Select Company or Individual as the supplier type.")

    existing, address, values = None, None, None
    if "address" in data or not name:
        if name:
            linked = _linked_addresses(name)
            if linked:
                _require("Address", "read")
                existing = _primary(name, _addresses(name, linked))
                if not existing:
                    frappe.throw("The linked supplier address needs attention in ERPNext.")
                address = frappe.get_doc("Address", existing["name"])
                address.check_permission("write")
        if not address:
            _require("Address", "create")
        values = _address_payload(data.get("address"), existing)
        if address and any(
            link.link_doctype != SUPPLIER or link.link_name != name for link in address.links
        ) and any((existing.get(field) or "") != values[field] for field in ADDRESS_FIELDS):
            frappe.throw("This address is shared. Update its links in ERPNext before changing it here.")

    supplier.update({"supplier_name": supplier_name, "supplier_group": group, "supplier_type": kind})
    for field in ("mobile_no", "email_id"):
        if field in data and supplier.meta.has_field(field):
            supplier.set(field, str(data[field] or "").strip())
    supplier.save() if name else supplier.insert()

    if values is not None:
        if address:
            if any((existing.get(field) or "") != values[field] for field in ADDRESS_FIELDS):
                address.update(values)
                address.save()
        else:
            address = frappe.get_doc({"doctype": "Address", "address_title": supplier_name,
                                      "address_type": "Billing", "is_primary_address": 1,
                                      "links": [{"link_doctype": SUPPLIER, "link_name": supplier.name}], **values})
            address.insert()
        if supplier.meta.has_field(PRIMARY) and supplier.get(PRIMARY) != address.name:
            supplier.db_set(PRIMARY, address.name)

    return {"name": supplier.name, "supplier_name": supplier.supplier_name, "supplier_group": supplier.supplier_group,
            "supplier_type": supplier.supplier_type, "mobile_no": supplier.get("mobile_no"), "email_id": supplier.get("email_id"),
            "can_edit": bool(frappe.has_permission(SUPPLIER, ptype="write", doc=supplier))}
