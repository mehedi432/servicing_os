"""Resolve ERPNext v15 serial bundles for an already authorized voucher."""

import frappe


def voucher_serials(voucher, lines):
    sources = {row.get("serial_and_batch_bundle"): row for row in lines if row.get("serial_and_batch_bundle")}
    if not sources:
        return {}
    bundles = frappe.get_all(
        "Serial and Batch Bundle",
        filters={"name": ["in", list(sources)], "voucher_type": voucher.doctype,
                 "voucher_no": voucher.name, "company": voucher.company},
        fields=["name", "voucher_detail_no", "item_code"],
    )
    verified = {bundle.name: bundle.voucher_detail_no for bundle in bundles
                if bundle.voucher_detail_no == sources[bundle.name].name
                and bundle.item_code == sources[bundle.name].item_code}
    if not verified:
        return {}
    entries = frappe.get_all(
        "Serial and Batch Entry",
        filters={"parenttype": "Serial and Batch Bundle", "parent": ["in", list(verified)]},
        fields=["parent", "serial_no"], order_by="idx asc",
    )
    serials = {}
    for entry in entries:
        if entry.serial_no:
            serials.setdefault(verified[entry.parent], []).append(entry.serial_no)
    return {name: "\n".join(dict.fromkeys(values)) for name, values in serials.items()}
