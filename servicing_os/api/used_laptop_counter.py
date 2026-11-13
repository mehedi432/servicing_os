"""SERVICING OS Used Laptop lifecycle: intake, inspection, service and cash resale.

Intake/receipt is delegated to the already installed menu_extensions module.
Servicing notes are Item custom fields plus audited document comments (NOT ledger costs).
Cash resale submits a standard stock-updating Sales Invoice and Payment Entry in
one POST, with the exact OEM serial and an idempotency key.
"""
import re
from decimal import Decimal, InvalidOperation

import frappe
from frappe.utils import flt, now_datetime

COMPANY = "AL MODINA COMPUTERS LIMITED"
WAREHOUSE = "Used Laptops - AMCL"
GROUP = "Used Laptops"
CASH = "Cash - AMCL"
PRICE_LIST = "Standard Selling"
ITEM_PREFIX = "custom_sos_ul_"
INVOICE_ITEM_FIELD = "custom_sos_ul_item"
INVOICE_KEY_FIELD = "custom_sos_ul_checkout_key"
STATES = ("Inspection Pending", "Diagnosing", "Repairing", "Hold", "Ready for Sale", "Sold")
GRADES = ("A", "B", "C", "For Parts")

FIELDS = [
    ("service_status", "Used Laptop Status", "Select", "\n".join(STATES)),
    ("condition", "Used Laptop Condition", "Select", "\n".join(GRADES)),
    ("diagnosis", "Used Laptop Diagnosis", "Small Text", None),
    ("work_done", "Used Laptop Work Done", "Small Text", None),
    ("technician", "Used Laptop Technician", "Link", "User"),
    ("service_cost", "Used Laptop Tracked Repair Spend", "Currency", None),
    ("asking_price", "Used Laptop Asking Price", "Currency", None),
    ("warranty_days", "Used Laptop Warranty Days", "Int", None),
    ("last_service_at", "Used Laptop Last Service Update", "Datetime", None),
]


def _require(dt, action="read", doc=None):
    if not frappe.has_permission(dt, ptype=action, doc=doc):
        frappe.throw(f"{action.title()} access is required for {dt}.", frappe.PermissionError)


def _manager():
    user = frappe.session.user
    return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def _service_staff():
    return _manager() or "Service Technician" in frappe.get_roles(frappe.session.user)


def _money(value, label="Amount", can_zero=False):
    try:
        d = Decimal(str(value))
        if not d.is_finite():
            raise ValueError()
        d = d.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        frappe.throw(f"{label} must be a valid BDT amount.")
    if d < 0 or d > Decimal("100000000") or (not can_zero and d == 0):
        frappe.throw(f"{label} must be {'zero or positive' if can_zero else 'greater than zero'}.")
    return d


def _item(code):
    _require("Item")
    code = str(code or "")
    if not frappe.db.exists("Item", code):
        frappe.throw("Used laptop not found.")
    item = frappe.get_doc("Item", code)
    item.check_permission("read")
    if item.item_group != GROUP or not item.has_serial_no or item.disabled:
        frappe.throw("Only active serialized Used Laptops can be processed here.")
    return item


def _serial_and_qty(item):
    # SOS_SERIAL_BUNDLE_LOOKUP_625A
    # Version 15 can store the OEM serial in a Serial and Batch Bundle rather
    # than Purchase Receipt Item.serial_no. Handle both; never invent a serial.
    fields = ["parent", "serial_no", "warehouse"]
    if frappe.get_meta("Purchase Receipt Item").has_field("serial_and_batch_bundle"):
        fields.append("serial_and_batch_bundle")
    rows = frappe.get_all("Purchase Receipt Item", filters={"item_code": item.name},
                          fields=fields, limit_page_length=100, order_by="creation desc")
    receipt_ids = list(dict.fromkeys(r.parent for r in rows))
    receipts = {r.name: r for r in frappe.get_all("Purchase Receipt",
        filters={"name": ["in", receipt_ids], "company": COMPANY},
        fields=["name", "docstatus", "supplier", "posting_date"],
        limit_page_length=100)} if receipt_ids else {}
    chosen = None
    for row in rows:
        p = receipts.get(row.parent)
        if not p or row.warehouse != WAREHOUSE or p.docstatus == 2:
            continue
        serial = (row.serial_no or "").strip()
        bundle = row.get("serial_and_batch_bundle") or ""
        if not serial and bundle:
            # An outward bundle belongs to a different stock transaction;
            # only read the inward receipt bundle linked to this receipt row.
            entries = frappe.get_all("Serial and Batch Entry",
                filters={"parent": bundle}, fields=["serial_no"], limit_page_length=3)
            found = [e.serial_no for e in entries if e.serial_no]
            if len(found) == 1:
                serial = found[0]
        candidate = {"receipt": p.name, "docstatus": p.docstatus,
                     "supplier": p.supplier, "serial": serial, "bundle": bundle}
        if chosen is None or (p.docstatus == 1 and chosen["docstatus"] != 1):
            chosen = candidate
        if p.docstatus == 1:
            break
    qty = flt(frappe.db.get_value("Bin", {"item_code": item.name,
                                            "warehouse": WAREHOUSE}, "actual_qty"))
    if chosen:
        serial = chosen["serial"]
        if not serial and chosen["docstatus"] == 1:
            # There is exactly one physical unit per used-laptop Item.
            possible = frappe.get_all("Serial No", filters={"item_code": item.name,
                "warehouse": WAREHOUSE}, pluck="name", limit_page_length=2)
            if len(possible) == 1:
                serial = chosen["serial"] = possible[0]
        sn = frappe.db.get_value("Serial No", serial,
            ["item_code", "warehouse", "status"], as_dict=True) if serial else None
        chosen["serial_in_stock"] = bool(sn and sn.item_code == item.name and
                                         sn.warehouse == WAREHOUSE and qty >= 1)
    return chosen, qty


def _validate_sale_stock(item, chosen, qty):
    if not chosen or chosen.get("docstatus") != 1:
        frappe.throw("Receive the laptop into stock before selling it.")
    if not chosen.get("serial") or not chosen.get("serial_in_stock") or qty < 1:
        frappe.throw("This OEM serial is not in the Used Laptops warehouse. Verify its stock receipt.")
    if item.get(ITEM_PREFIX + "service_status") != "Ready for Sale":
        frappe.throw("Complete inspection and set the laptop to Ready for Sale first.")


def setup():
    """Create metadata only. Called by installer, not by staff UI."""
    if not frappe.db.exists("Company", COMPANY):
        frappe.throw("AMCL company missing.")
    if not frappe.db.exists("Item Group", GROUP):
        frappe.throw("Used Laptops Item Group missing; install 6.21–6.23 first.")
    created = []
    entries = [("Item", ITEM_PREFIX + key, label, fieldtype, opts)
               for key, label, fieldtype, opts in FIELDS]
    entries.extend([
        ("Sales Invoice", INVOICE_ITEM_FIELD, "SERVICING OS Used Laptop", "Link", "Item"),
        ("Sales Invoice", INVOICE_KEY_FIELD, "SERVICING OS Used Laptop Checkout Key", "Data", None),
    ])
    for dt, name, label, typ, opt in entries:
        meta = frappe.get_meta(dt)
        field = meta.get_field(name)
        if field:
            if field.fieldtype != typ or ((opt or "") != (field.options or "")):
                frappe.throw(f"Existing field {dt}.{name} is incompatible; stopped safely.")
            if name == INVOICE_KEY_FIELD and not field.unique:
                frappe.throw("Existing resale idempotency field is not unique; stopped safely.")
            continue
        info = {"doctype": "Custom Field", "dt": dt, "fieldname": name,
                "label": label, "fieldtype": typ, "hidden": 1, "no_copy": 1}
        if opt:
            info["options"] = opt
        if name == INVOICE_KEY_FIELD:
            info.update(unique=1, read_only=1)
        if name == INVOICE_ITEM_FIELD:
            info["read_only"] = 1
        frappe.get_doc(info).insert(ignore_permissions=True)
        created.append(f"{dt}.{name}")
        frappe.clear_cache(doctype=dt)
    return {"ok": True, "created_fields": created}


@frappe.whitelist(methods=["GET"])
def get_workspace(search=""):
    _require("Item")
    from servicing_os.api.menu_extensions import get_laptop_hub
    hub = get_laptop_hub(search=search)
    names = [x["name"] for x in hub.get("items", [])]
    custom = [ITEM_PREFIX + f[0] for f in FIELDS]
    fieldnames = ["name", "item_name", "stock_uom"] + custom
    if names:
        for r in frappe.get_list("Item", filters={"name": ["in", names]},
                                 fields=fieldnames, limit_page_length=150):
            doc = next((x for x in hub["items"] if x["name"] == r.name), None)
            if doc:
                doc.update({k: r.get(k) for k in custom})
    for x in hub.get("items", []):
        stock_receipt, qty = _serial_and_qty(frappe._dict(x))
        x["intake"] = stock_receipt
        x["actual_qty"] = qty
        x["status"] = (x.get(ITEM_PREFIX + "service_status") or
            ("Inspection Pending" if qty > 0 else "Awaiting Stock Receipt"))
        x["can_sell"] = bool(qty > 0 and stock_receipt and
            stock_receipt.get("serial_in_stock") and x["status"] == "Ready for Sale")
    hub["can_service"] = _service_staff()
    hub["can_price"] = _manager()
    hub["can_cash_sale"] = all(frappe.has_permission(dt, ptype=a) for dt in
        ("Sales Invoice", "Payment Entry") for a in ("create", "submit"))
    hub["can_create_customer"] = frappe.has_permission("Customer", "create")
    hub["stock_only_note"] = "Tracked repair spend is operational, not an accounting expense or capitalized cost."
    if frappe.has_permission("Sales Invoice", "read") and names:
        posted_sales = frappe.get_list("Sales Invoice",
            filters={"company": COMPANY, "docstatus": 1, INVOICE_ITEM_FIELD: ["in", names]},
            fields=["name", INVOICE_ITEM_FIELD], limit_page_length=150)
        sold = {d.get(INVOICE_ITEM_FIELD): d.name for d in posted_sales}
        for row in hub.get("items", []):
            if row["name"] in sold and row["actual_qty"] < 1:
                row["status"] = "Sold"
                row["sold_invoice"] = sold[row["name"]]
                row["can_sell"] = False
    hub["service_statuses"] = STATES[:-1]
    hub["condition_grades"] = GRADES
    return hub


@frappe.whitelist(methods=["GET"])
def get_service_history(item_code):
    item = _item(item_code)
    _require("Comment")
    return {"events": [dict(x) for x in frappe.get_list("Comment",
        filters={"reference_doctype": "Item", "reference_name": item.name,
                 "comment_type": "Comment"},
        fields=["creation", "comment_by", "content"],
        order_by="creation desc", limit_page_length=40)]}


@frappe.whitelist(methods=["POST"])
def save_service(item_code, status, condition, diagnosis="", work_done="", technician="",
                 repair_spend="", asking_price="", warranty_days="0"):
    if not _service_staff():
        frappe.throw("Only a Service Technician or System Manager can update refurbishment.", frappe.PermissionError)
    item = _item(item_code)
    intake, qty = _serial_and_qty(item)
    if not intake or intake["docstatus"] != 1 or qty < 1 or not intake["serial_in_stock"]:
        frappe.throw("Receive the physical laptop into stock before recording refurbishment.")
    status = str(status or "").strip()
    condition = str(condition or "").strip()
    if status not in STATES[:-1] or condition not in GRADES:
        frappe.throw("Choose a valid repair status and condition grade.")
    diagnosis = str(diagnosis or "").strip()[:1800]
    work_done = str(work_done or "").strip()[:1800]
    technician = str(technician or "").strip()
    if technician and (not frappe.db.exists("User", technician) or not frappe.db.get_value("User", technician, "enabled")):
        frappe.throw("Choose an active technician user.")
    if status == "Ready for Sale" and (not condition or not (diagnosis or work_done)):
        frappe.throw("Record the inspection findings or completed work before marking Ready for Sale.")
    old_spend = _money(item.get(ITEM_PREFIX + "service_cost") or 0, "Tracked spend", True)
    old_price = _money(item.get(ITEM_PREFIX + "asking_price") or 0, "Asking price", True)
    spend = old_spend if repair_spend in ("", None) else _money(repair_spend, "Tracked repair spend", True)
    price = old_price if asking_price in ("", None) else _money(asking_price, "Asking price", True)
    try:
        warranty = int(warranty_days or 0)
    except (ValueError, TypeError):
        frappe.throw("Warranty days must be a whole number.")
    if warranty < 0 or warranty > 1095:
        frappe.throw("Warranty days must be 0–1095.")
    if not _manager() and (spend != old_spend or price != old_price):
        frappe.throw("Only a manager may change selling prices or tracked repair spend.", frappe.PermissionError)
    values = {
        ITEM_PREFIX + "service_status": status,
        ITEM_PREFIX + "condition": condition,
        ITEM_PREFIX + "diagnosis": diagnosis,
        ITEM_PREFIX + "work_done": work_done,
        ITEM_PREFIX + "technician": technician or None,
        ITEM_PREFIX + "service_cost": float(spend),
        ITEM_PREFIX + "asking_price": float(price),
        ITEM_PREFIX + "warranty_days": warranty,
        ITEM_PREFIX + "last_service_at": now_datetime(),
    }
    # Narrow explicit role-based write; no general permission bypass endpoint.
    if frappe.has_permission("Item", "write", item.name):
        for k, v in values.items():
            item.set(k, v)
        item.save()
    else:
        for k, v in values.items():
            frappe.db.set_value("Item", item.name, k, v, update_modified=False)
        frappe.db.set_value("Item", item.name, "modified", now_datetime(), update_modified=False)
    detail = (f"Used laptop service updated by {frappe.session.user}: "
        f"{status}, grade {condition}. "
        f"Diagnosis: {diagnosis or 'Not specified'}; "
        f"Work: {work_done or 'Not specified'}. "
        f"Tracked repair spend: BDT {spend}. Asking price: BDT {price}. "
        f"Repair spend is not a posted accounting expense.")
    frappe.get_doc({"doctype": "Comment", "comment_type": "Comment",
        "reference_doctype": "Item", "reference_name": item.name,
        "content": detail}).insert(ignore_permissions=True)
    return {"ok": True, "item_code": item.name, "status": status,
            "message": "Refurbishment saved to the laptop record. No stock or ledger movement."}


def _build_invoice(item_code, customer, rate, key=None):
    _require("Customer")
    item = _item(item_code)
    intake, qty = _serial_and_qty(item)
    _validate_sale_stock(item, intake, qty)
    if not frappe.db.exists("Customer", customer) or frappe.db.get_value("Customer", customer, "disabled"):
        frappe.throw("Select an active customer.")
    _require("Customer", "read", customer)
    rate = _money(rate, "Selling price")
    if not item.is_sales_item:
        frappe.throw("This laptop Item is not marked for sale.")
    row = {"item_code": item.name, "qty": 1, "uom": item.stock_uom,
           "conversion_factor": 1, "rate": float(rate), "price_list_rate": float(rate),
           "warehouse": WAREHOUSE, "serial_no": intake["serial"]}
    if frappe.get_meta("Sales Invoice Item").has_field("use_serial_batch_fields"):
        row["use_serial_batch_fields"] = 1
    invoice = frappe.get_doc({"doctype": "Sales Invoice", "company": COMPANY,
        "customer": customer, "currency": "BDT", "selling_price_list": PRICE_LIST,
        "set_warehouse": WAREHOUSE, "update_stock": 1, "is_pos": 0,
        "ignore_pricing_rule": 1, "items": [row], INVOICE_ITEM_FIELD: item.name})
    if key:
        invoice.set(INVOICE_KEY_FIELD, key)
    invoice.run_method("set_missing_values")
    invoice.run_method("calculate_taxes_and_totals")
    if not invoice.update_stock or invoice.company != COMPANY or len(invoice.items) != 1:
        frappe.throw("Invoice defaults changed critical values; checkout stopped.")
    v = invoice.items[0]
    if (v.item_code != item.name or v.warehouse != WAREHOUSE or
        v.serial_no != intake["serial"] or _money(v.rate, "Final item rate") != rate):
        frappe.throw("Selected device, serial, warehouse or rate changed; checkout stopped.")
    if _money(invoice.grand_total, "Total") <= 0:
        frappe.throw("Calculated invoice total is invalid.")
    return invoice, intake


@frappe.whitelist(methods=["POST"])
def quote_cash_sale(item_code, customer, selling_price):
    invoice, intake = _build_invoice(item_code, customer, selling_price)
    return {"item_code": item_code, "customer": customer,
        "serial": intake["serial"], "net_total": float(_money(invoice.net_total)),
        "tax_total": float(_money(invoice.total_taxes_and_charges, "Tax", True)),
        "grand_total": float(_money(invoice.grand_total)), "currency": "BDT",
        "message": "Amounts may be recalculated at final submission."}


@frappe.whitelist(methods=["POST"])
def complete_cash_sale(item_code, customer, selling_price, expected_total, checkout_key):
    """Single atomic POST for an exact-serial stock invoice and its cash settlement."""
    for dt in ("Sales Invoice", "Payment Entry"):
        _require(dt, "create")
        _require(dt, "submit")
    token = str(checkout_key or "")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{16,64}", token):
        frappe.throw("Invalid sale confirmation key. Please review again.")
    old = frappe.db.get_value("Sales Invoice", {INVOICE_KEY_FIELD: token},
        ["name", "docstatus", "customer", INVOICE_ITEM_FIELD, "grand_total"], as_dict=True)
    if old:
        if old.docstatus == 1 and old.customer == customer and old.get(INVOICE_ITEM_FIELD) == item_code:
            return {"success": True, "already_processed": True,
                    "invoice": old.name, "total": flt(old.grand_total)}
        frappe.throw("This sale confirmation was already used. Refresh the screen.")
    cash = frappe.db.get_value("Account", CASH,
        ["company", "account_type", "account_currency", "is_group", "disabled"], as_dict=True)
    if not cash or cash.company != COMPANY or cash.account_type != "Cash" or cash.account_currency != "BDT" or cash.is_group or cash.disabled:
        frappe.throw("AMCL Cash account is not configured for counter receipts.")
    if not frappe.db.exists("Mode of Payment", "Cash"):
        frappe.throw("Cash mode of payment is missing.")
    invoice, intake = _build_invoice(item_code, customer, selling_price, key=token)
    if abs(_money(invoice.grand_total) - _money(expected_total)) > Decimal("0.01"):
        frappe.throw("Invoice amount changed. Review the sale total again before collecting cash.")
    invoice.insert()
    if abs(_money(invoice.grand_total) - _money(expected_total)) > Decimal("0.01"):
        frappe.throw("Invoice amount changed after validation; checkout not posted.")
    invoice.submit()  # Updates stock and creates the exact-serial stock movement.
    if invoice.docstatus != 1 or invoice.update_stock != 1:
        frappe.throw("Serial stock invoice was not confirmed; checkout rolled back.")
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    amount = flt(invoice.outstanding_amount)
    if amount <= 0:
        frappe.throw("Invoice outstanding amount is not payable by cash as expected.")
    payment = get_payment_entry("Sales Invoice", invoice.name, bank_account=CASH, bank_amount=amount)
    if (payment.payment_type != "Receive" or payment.party_type != "Customer" or
        payment.party != customer or payment.company != COMPANY):
        frappe.throw("Unexpected cash account allocation; checkout rolled back.")
    payment.mode_of_payment = "Cash"
    payment.paid_to = CASH
    payment.paid_amount = amount
    payment.received_amount = amount
    refs = [r for r in payment.references if r.reference_doctype == "Sales Invoice" and r.reference_name == invoice.name]
    if len(payment.references) != 1 or len(refs) != 1:
        frappe.throw("Unexpected invoice payment allocation; checkout rolled back.")
    refs[0].allocated_amount = amount
    payment.insert()
    payment.submit()
    if payment.docstatus != 1 or payment.paid_to != CASH:
        frappe.throw("Cash collection was not confirmed; checkout rolled back.")
    # Service status follows the *posted invoice*; invoice remains source of truth.
    frappe.db.set_value("Item", item_code, ITEM_PREFIX + "service_status", "Sold", update_modified=False)
    invoice.reload()
    return {"success": True, "invoice": invoice.name, "payment_entry": payment.name,
        "item_code": item_code, "serial": intake["serial"], "customer": customer,
        "total": float(_money(invoice.grand_total)), "outstanding": flt(invoice.outstanding_amount),
        "message": "Sale posted. Device removed from stock and cash collected."}


@frappe.whitelist(methods=["GET"])
def get_sale_receipt(invoice_name):
    _require("Sales Invoice", "read", invoice_name)
    inv = frappe.get_doc("Sales Invoice", invoice_name)
    inv.check_permission("read")
    if inv.docstatus != 1 or inv.company != COMPANY or not inv.get(INVOICE_ITEM_FIELD):
        frappe.throw("Not a posted SERVICING OS used-laptop sale.")
    if len(inv.items) != 1 or inv.items[0].item_code != inv.get(INVOICE_ITEM_FIELD):
        frappe.throw("Unexpected invoice details; cannot print this receipt.")
    return {"invoice": inv.name, "posting_date": str(inv.posting_date),
        "company": COMPANY, "customer": inv.customer_name or inv.customer,
        "item_code": inv.items[0].item_code, "item_name": inv.items[0].item_name,
        "serial": inv.items[0].serial_no, "rate": inv.items[0].rate,
        "tax_total": inv.total_taxes_and_charges, "grand_total": inv.grand_total,
        "outstanding": inv.outstanding_amount, "currency": "BDT"}
