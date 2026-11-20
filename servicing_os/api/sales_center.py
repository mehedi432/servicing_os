"""SERVICING OS sales centre; Frappe 15 / ERPNext 15.

All writes use normal ERPNext documents, permission checks and validations.
There are no direct SQL mutations to ledgers or stock and no ignore_permissions.
"""
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, add_days, nowdate
from servicing_os.api.site_company_706 import current_company, retail_warehouse, selling_price_list

DOCTYPES = {
    "invoice": "Sales Invoice", "quotation": "Quotation",
    "payment": "Payment Entry", "return": "Sales Invoice"
}


def _auth():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please sign in."), frappe.PermissionError)


def _check(doctype, permission):
    _auth()
    if not frappe.has_permission(doctype, permission):
        frappe.throw(_("You do not have permission to {0} {1}.").format(permission, doctype), frappe.PermissionError)


def _shop():
    _auth()
    return {"company": current_company(), "warehouse": retail_warehouse(), "price_list": selling_price_list()}


def _invoice(name):
    _check("Sales Invoice", "read")
    if not name or len(str(name)) > 140:
        frappe.throw(_("Invalid sales invoice."))
    doc = frappe.get_doc("Sales Invoice", name)
    doc.check_permission("read")
    if doc.company != current_company():
        frappe.throw(_("This invoice belongs to another company."), frappe.PermissionError)
    return doc


@frappe.whitelist(methods=["GET"])
def configuration():
    cfg = _shop()
    perms = {doctype: {op: bool(frappe.has_permission(doctype, op)) for op in ("read", "create", "submit", "write")}
             for doctype in ("Sales Invoice", "Quotation", "Payment Entry", "Item", "Customer")}
    modes = []
    if perms["Payment Entry"]["create"]:
        modes = frappe.get_all("Mode of Payment", filters={"enabled": 1}, fields=["name"], limit_page_length=50)
    return dict(cfg, permissions=perms, modes=[x.name for x in modes], currency=frappe.db.get_value("Company", current_company(), "default_currency") or "BDT")


@frappe.whitelist(methods=["GET"])
def customers(q=""):
    _check("Customer", "read")
    q = str(q or "").strip()[:80]
    if len(q) < 2:
        return []
    matches = frappe.get_list("Customer", filters={"disabled": 0} if frappe.get_meta("Customer").has_field("disabled") else {},
                              or_filters={"name": ["like", "%" + q + "%"], "customer_name": ["like", "%" + q + "%"]},
                              fields=["name", "customer_name"], limit_page_length=15)
    return [dict(x) for x in matches]


@frappe.whitelist(methods=["GET"])
def catalog(q=""):
    _check("Item", "read")
    q = str(q or "").strip()[:80]
    if len(q) < 2:
        return []
    cfg = _shop()
    items = frappe.get_list("Item", filters={"disabled": 0, "is_sales_item": 1},
                            or_filters={"item_code": ["like", "%" + q + "%"], "item_name": ["like", "%" + q + "%"]},
                            fields=["name", "item_name", "stock_uom", "has_serial_no", "is_stock_item", "warranty_period"],
                            limit_page_length=25)
    result = []
    for item in items:
        price = frappe.db.get_value("Item Price", {"item_code": item.name, "price_list": cfg["price_list"], "selling": 1}, "price_list_rate")
        stock = frappe.db.get_value("Bin", {"item_code": item.name, "warehouse": cfg["warehouse"]}, "actual_qty")
        result.append(dict(item_code=item.name, item_name=item.item_name, uom=item.stock_uom,
                           rate=flt(price), stock_qty=flt(stock), serialized=bool(item.has_serial_no),
                           is_stock_item=bool(item.is_stock_item), warranty_months=cint(item.warranty_period)))
    return result


@frappe.whitelist(methods=["GET"])
def records(kind="invoice", query="", limit=50):
    doctype = DOCTYPES.get(kind)
    if not doctype:
        frappe.throw(_("Invalid document type."))
    _check(doctype, "read")
    n = max(1, min(cint(limit or 50), 100))
    q = str(query or "").strip()[:80]
    if kind == "quotation":
        fields = ["name", "transaction_date", "party_name", "status", "grand_total", "docstatus"]
        filters = {"company": current_company()}
    elif kind == "payment":
        fields = ["name", "posting_date", "party", "mode_of_payment", "paid_amount", "docstatus"]
        filters = {"company": current_company(), "payment_type": "Receive", "party_type": "Customer"}
    else:
        fields = ["name", "posting_date", "customer", "customer_name", "grand_total", "outstanding_amount", "status", "is_return", "docstatus"]
        filters = {"company": current_company()}
        if kind == "return":
            filters["is_return"] = 1
    if q:
        # Prefix search only on name, so we do not leak inaccessible customers.
        filters["name"] = ["like", "%" + q + "%"]
    rows = frappe.get_list(doctype, fields=fields, filters=filters,
                           order_by="modified desc", limit_page_length=n)
    return [dict(r) for r in rows]


@frappe.whitelist(methods=["GET"])
def invoice_detail(name):
    d = _invoice(name)
    return {"name": d.name, "customer": d.customer, "customer_name": d.customer_name,
            "posting_date": str(d.posting_date), "status": d.status, "docstatus": d.docstatus,
            "grand_total": d.grand_total, "outstanding_amount": d.outstanding_amount,
            "is_return": d.is_return, "return_against": d.return_against,
            "payments": [{"mode": x.mode_of_payment, "amount": x.amount} for x in (d.payments or [])],
            "items": [{"name": x.name, "item_code": x.item_code, "item_name": x.item_name,
                       "qty": x.qty, "rate": x.rate, "amount": x.amount,
                       "serial_no": x.serial_no,
                       "warranty_days": cint(x.get("custom_sos_warranty_days") or 0),
                       "warranty_expiry": str(x.get("custom_sos_warranty_expiry") or "")}
                      for x in d.items]}


def _items(payload):
    _check("Item", "read")
    cfg = _shop()
    if not isinstance(payload, list) or not payload or len(payload) > 50:
        frappe.throw(_("Add 1 to 50 products."))
    out = []
    for raw in payload:
        code = str(raw.get("item_code") or "")[:140]
        qty = flt(raw.get("qty"), 6)
        if not code or not (0 < qty <= 100000):
            frappe.throw(_("Invalid product or quantity."))
        item = frappe.get_doc("Item", code)
        item.check_permission("read")
        if item.disabled or not item.is_sales_item:
            frappe.throw(_("Item {0} is not available for sale.").format(code))
        rate = frappe.db.get_value("Item Price", {"item_code": code, "price_list": cfg["price_list"], "selling": 1}, "price_list_rate")
        if rate is None or flt(rate) < 0:
            frappe.throw(_("Set a selling price for {0} first.").format(code))
        out.append({"item_code": code, "qty": qty, "rate": flt(rate), "uom": item.stock_uom, "warehouse": cfg["warehouse"]})
    return out


@frappe.whitelist(methods=["POST"])
def create_quotation(customer=None, items=None, valid_till=None):
    _check("Quotation", "create")
    _check("Customer", "read")
    if not customer or not frappe.db.exists("Customer", customer):
        frappe.throw(_("Choose an existing customer."))
    if not frappe.has_permission("Customer", "read", customer):
        frappe.throw(_("Customer access denied."), frappe.PermissionError)
    if isinstance(items, str):
        items = frappe.parse_json(items)
    cfg = _shop()
    date = getdate(valid_till) if valid_till else add_days(nowdate(), 14)
    if date < getdate(nowdate()):
        frappe.throw(_("Validity date cannot be in the past."))
    doc = frappe.get_doc({"doctype": "Quotation", "company": cfg["company"],
                          "quotation_to": "Customer", "party_name": customer,
                          "transaction_date": nowdate(), "valid_till": date,
                          "selling_price_list": cfg["price_list"], "items": _items(items)})
    doc.insert()
    return {"name": doc.name, "status": "Draft", "grand_total": doc.grand_total}


@frappe.whitelist(methods=["POST"])
def submit_quotation(name):
    _check("Quotation", "submit")
    doc = frappe.get_doc("Quotation", name)
    doc.check_permission("submit")
    if doc.company != current_company() or doc.docstatus != 0:
        frappe.throw(_("Only a draft quotation for this company may be submitted."))
    doc.submit()
    return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def create_return_draft(invoice, quantities=None):
    """Use ERPNext's own return mapping; never credit arbitrary items/rates."""
    _check("Sales Invoice", "create")
    source = _invoice(invoice)
    if source.docstatus != 1 or source.is_return:
        frappe.throw(_("Select a submitted original sales invoice."))
    from erpnext.controllers.sales_and_purchase_return import make_return_doc
    ret = make_return_doc("Sales Invoice", source.name)
    if quantities is not None:
        if isinstance(quantities, str):
            quantities = frappe.parse_json(quantities)
        if not isinstance(quantities, dict):
            frappe.throw(_("Return quantities must be a mapping of original invoice item row to quantity."))
        originals = {x.name: x for x in source.items}
        kept = []
        for row in ret.items:
            original_key = row.get("si_detail") or row.get("sales_invoice_item")
            if not original_key or original_key not in originals:
                # Some ERPNext point releases omit the original detail reference.
                # Only recover it when the item code is unique on the source sale.
                unique = [x.name for x in source.items if x.item_code == row.item_code]
                original_key = unique[0] if len(unique) == 1 else None
            if not original_key or original_key not in originals:
                frappe.throw(_("Unable to safely map returned row to original invoice line. Use the serial-specific return workflow."))
            original_row = originals[original_key]
            qty = flt(quantities.get(original_key, 0), 6)
            if not (0 <= qty <= abs(flt(original_row.qty))):
                frappe.throw(_("Return quantity cannot exceed original sold quantity."))
            serialized = bool(
                original_row.serial_no
                or original_row.get("serial_and_batch_bundle")
                or frappe.db.get_value("Item", original_row.item_code, "has_serial_no")
            )
            if qty and serialized and abs(qty - abs(flt(original_row.qty))) > 0.000001:
                frappe.throw(_("Partial serialized returns require individual serial selection and are blocked in this quick workflow."))
            if qty:
                row.qty = -abs(qty)
                kept.append(row)
        if not kept:
            frappe.throw(_("Select at least one item to return."))
        ret.set("items", kept)
    ret.insert()
    return {"name": ret.name, "status": "Draft", "original": invoice,
            "message": "Review quantities, serial numbers and refund before submitting."}


@frappe.whitelist(methods=["POST"])
def submit_return(name):
    _check("Sales Invoice", "submit")
    doc = frappe.get_doc("Sales Invoice", name)
    doc.check_permission("submit")
    if doc.company != current_company() or not doc.is_return or doc.docstatus != 0:
        frappe.throw(_("Only a draft return for this company can be submitted."))
    if not doc.return_against:
        frappe.throw(_("Original invoice is required."))
    doc.submit()
    return {"name": doc.name, "status": doc.status, "note": "Credit note submitted; refund/payment reconciliation is a separate transaction."}


@frappe.whitelist(methods=["POST"])
def receive_payment(invoice, amount, mode_of_payment, reference_no=None, reference_date=None):
    _check("Payment Entry", "create")
    _check("Payment Entry", "submit")
    source = _invoice(invoice)
    if source.docstatus != 1 or source.is_return or flt(source.outstanding_amount) <= 0:
        frappe.throw(_("This invoice has no collectible outstanding amount."))
    amt = flt(amount, 2)
    if not (0 < amt <= flt(source.outstanding_amount, 2)):
        frappe.throw(_("Payment must be positive and within the outstanding amount."))
    mode = frappe.get_doc("Mode of Payment", mode_of_payment)
    if not mode.enabled:
        frappe.throw(_("Payment mode is disabled."))
    account = next((x.default_account for x in mode.accounts if x.company == current_company() and x.default_account), None)
    if not account:
        frappe.throw(_("Configure the company account for this payment mode before collecting money."))
    if source.currency != (frappe.db.get_value("Company", current_company(), "default_currency") or "BDT"):
        frappe.throw(_("Foreign-currency payments require the standard ERPNext multi-currency payment workflow."))
    account_currency = frappe.db.get_value("Account", account, "account_currency")
    if account_currency and account_currency != source.currency:
        frappe.throw(_("Payment account currency must match the invoice currency in this quick collection workflow."))
    if mode.type == "Bank" and not reference_no:
        frappe.throw(_("Bank or mobile banking payments require a transaction reference."))
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    pe = get_payment_entry("Sales Invoice", source.name, party_amount=amt)
    pe.mode_of_payment = mode.name
    pe.paid_to = account
    pe.paid_amount = amt
    pe.received_amount = amt
    if reference_no:
        pe.reference_no = str(reference_no)[:140]
        pe.reference_date = getdate(reference_date) if reference_date else getdate(nowdate())
    for row in pe.references:
        if row.reference_name == source.name:
            row.allocated_amount = amt
    pe.insert()
    pe.submit()
    return {"name": pe.name, "invoice": source.name, "amount": amt}


@frappe.whitelist(methods=["POST"])
def set_warranty(invoice, item_row, days):
    """Non-accounting warranty metadata, editable on submitted invoice items."""
    _check("Sales Invoice", "write")
    d = _invoice(invoice)
    d.check_permission("write")
    days = cint(days)
    if not (0 <= days <= 3650):
        frappe.throw(_("Warranty must be between 0 and 3650 days."))
    row = next((x for x in d.items if x.name == item_row), None)
    if not row:
        frappe.throw(_("Invoice item row not found."))
    meta = frappe.get_meta("Sales Invoice Item")
    if not (meta.has_field("custom_sos_warranty_days") and meta.has_field("custom_sos_warranty_expiry")):
        frappe.throw(_("Warranty custom fields are not installed. Run sales setup first."))
    row.custom_sos_warranty_days = days
    row.custom_sos_warranty_expiry = add_days(d.posting_date, days) if days else None
    d.save()
    return {"invoice": d.name, "item_row": row.name, "days": days,
            "expiry": str(row.custom_sos_warranty_expiry or "")}


def ensure_warranty_fields():
    """Run as bench administrator once. Adds only editable non-ledger custom fields."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({"Sales Invoice Item": [
        {"fieldname": "custom_sos_warranty_days", "label": "Servicing Warranty Days", "fieldtype": "Int", "default": "0", "allow_on_submit": 1, "insert_after": "description"},
        {"fieldname": "custom_sos_warranty_expiry", "label": "Servicing Warranty Expiry", "fieldtype": "Date", "read_only": 1, "allow_on_submit": 1, "insert_after": "custom_sos_warranty_days"}
    ]}, update=False)
    frappe.clear_cache(doctype="Sales Invoice Item")
    return "Warranty fields installed"


@frappe.whitelist(methods=["GET"])
def statistics(from_date=None, to_date=None):
    _check("Sales Invoice", "read")
    to_date = getdate(to_date or nowdate())
    from_date = getdate(from_date or add_days(to_date, -29))
    if (to_date - from_date).days < 0 or (to_date - from_date).days > 366:
        frappe.throw(_("Choose a valid range of up to 366 days."))
    # Permissions respected by frappe.get_list. Hard result cap disclosed to clients.
    rows = frappe.get_list("Sales Invoice", filters={"company": current_company(), "docstatus": 1,
                        "posting_date": ["between", [str(from_date), str(to_date)]]},
                        fields=["name", "posting_date", "grand_total", "outstanding_amount", "is_return", "is_pos", "paid_amount"],
                        limit_page_length=5001)
    limited = len(rows) > 5000
    rows = rows[:5000]
    sales = sum(flt(x.grand_total) for x in rows if not x.is_return)
    returns = sum(abs(flt(x.grand_total)) for x in rows if x.is_return)
    dues = sum(flt(x.outstanding_amount) for x in rows if not x.is_return)
    pos_collection = sum(flt(x.paid_amount) for x in rows if x.is_pos and not x.is_return)
    payments = []
    if frappe.has_permission("Payment Entry", "read"):
        payments = frappe.get_list("Payment Entry", filters={"company": current_company(), "docstatus": 1,
                            "payment_type": "Receive", "party_type": "Customer",
                            "posting_date": ["between", [str(from_date), str(to_date)]]},
                            fields=["name", "received_amount"], limit_page_length=5001)
    payments_limited = len(payments) > 5000
    collected = pos_collection + sum(flt(x.received_amount) for x in payments[:5000])
    return {"from_date": str(from_date), "to_date": str(to_date), "invoice_count": len([x for x in rows if not x.is_return]),
            "sales": round(sales, 2), "returns": round(returns, 2), "net_sales": round(sales-returns, 2),
            "outstanding": round(dues, 2), "collections": round(collected, 2),
            "payment_count": len(payments[:5000]), "collections_visible": bool(frappe.has_permission("Payment Entry", "read")),
            "limited": limited or payments_limited}


def release_readiness():
    """Read-only preflight. Run with bench execute as an administrator."""
    company_exists = bool(frappe.db.exists("Company", current_company()))
    wh = frappe.db.get_value("Warehouse", retail_warehouse(), ["company", "is_group", "disabled"], as_dict=True)
    profiles = frappe.get_all("POS Profile", filters={"company": current_company(), "disabled": 0},
                              fields=["name", "warehouse", "selling_price_list"], limit_page_length=50)
    prices = frappe.db.count("Item Price", {"price_list": selling_price_list(), "selling": 1})
    modes = frappe.get_all("Mode of Payment", filters={"enabled": 1}, fields=["name"], limit_page_length=50)
    configured_modes = []
    for m in modes:
        account = frappe.db.get_value("Mode of Payment Account", {"parent": m.name, "company": current_company()}, "default_account")
        if account:
            configured_modes.append({"mode": m.name, "account": account})
    meta = frappe.get_meta("Sales Invoice Item")
    result = {
        "company": current_company(), "company_exists": company_exists,
        "retail_warehouse": retail_warehouse(), "warehouse_usable": bool(wh and wh.company == current_company() and not wh.is_group and not wh.disabled),
        "active_pos_profiles": [dict(x) for x in profiles],
        "standard_selling_item_prices": prices,
        "configured_collection_modes": configured_modes,
        "warranty_fields_present": meta.has_field("custom_sos_warranty_days") and meta.has_field("custom_sos_warranty_expiry"),
        "frappe_version": frappe.__version__
    }
    print(frappe.as_json(result, indent=2))
    return result
