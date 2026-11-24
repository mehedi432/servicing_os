"""Add supplementary warranty fields without rewriting existing transactions."""

import frappe
from frappe.utils import cint

RECEIPT_FIELDS = {
    "custom_sos_supplier_coverage": ("Select", "Supplier Coverage Type", "\nSupplier Warranty\nManufacturer Warranty\nNo Warranty"),
    "custom_sos_supplier_warranty_start": ("Date", "Supplier Warranty Start", None),
    "custom_sos_supplier_warranty_end": ("Date", "Supplier Warranty Expiry", None),
    "custom_sos_supplier_warranty_ref": ("Data", "Supplier Warranty Reference", None),
    "custom_sos_supplier_warranty_terms": ("Small Text", "Supplier Warranty Terms", None),
}
CLAIM_FIELDS = {
    "custom_sos_warranty_sale_type": ("Link", "Warranty Invoice Type", "DocType"),
    "custom_sos_warranty_sale": ("Dynamic Link", "Warranty Invoice", "custom_sos_warranty_sale_type"),
    "custom_sos_supplier_rma": ("Data", "Supplier RMA Reference", None),
}
FIELDS = {"Purchase Receipt Item": RECEIPT_FIELDS, "Warranty Claim": CLAIM_FIELDS}

def _matches(field, kind, options):
    if field.fieldtype != kind or (options is not None and kind != "Select" and field.options != options):
        return False
    if kind == "Select":
        return (field.options or "").strip().splitlines() == options.strip().splitlines()
    return True

def ensure():
    if frappe.session.user != "Administrator" and not frappe.has_permission("Custom Field", "create"):
        frappe.throw("Custom Field create permission is required.", frappe.PermissionError)

    created = []
    for doctype, fields in FIELDS.items():
        anchor = "qty" if doctype == "Purchase Receipt Item" else "resolution_details"
        for name, (kind, label, options) in fields.items():
            field = frappe.get_meta(doctype).get_field(name)
            if field:
                if not _matches(field, kind, options):
                    frappe.throw(f"{doctype}.{name} has incompatible settings.")
            else:
                doc = {"doctype": "Custom Field", "dt": doctype, "fieldname": name, "label": label,
                       "fieldtype": kind, "insert_after": anchor, "no_copy": 1, "print_hide": 1,
                       "allow_on_submit": int(doctype == "Purchase Receipt Item")}
                if options:
                    doc["options"] = options
                frappe.get_doc(doc).insert()
                frappe.clear_cache(doctype=doctype)
                created.append(f"{doctype}.{name}")
            anchor = name
    verify()
    return {"created": created}


def verify():
    for doctype, fields in FIELDS.items():
        meta = frappe.get_meta(doctype, cached=False)
        for name, (kind, _, options) in fields.items():
            field = meta.get_field(name)
            if (not field or not _matches(field, kind, options)
                    or (doctype == "Purchase Receipt Item" and not cint(field.allow_on_submit))
                    or not frappe.db.has_column(doctype, name)):
                frappe.throw(f"{doctype}.{name} is missing or incompatible. Run bench migrate.")
    return True
