# SERVICING_COUNTER_620E
"""Custom counter workflow. Underlying documents are standard Sales Invoice + Payment Entry.
No POS Profile or external checkout UI required. Cash-only, ordinary stock Items only.
"""
import json
import re
from decimal import Decimal, InvalidOperation
import frappe
from frappe.utils import flt, getdate, nowdate

COMPANY = "AL MODINA COMPUTERS LIMITED"
WAREHOUSE = "Stores - AMCL"
PRICE_LIST = "Standard Selling"
CASH_ACCOUNT = "Cash - AMCL"
FIELD = "custom_servicing_counter_key"


def _require(doctype, right):
    if not frappe.has_permission(doctype, ptype=right):
        frappe.throw(f"Not permitted to {right}: {doctype}", frappe.PermissionError)


def _money(value):
    try:
        d = Decimal(str(value))
        if not d.is_finite():
            raise ValueError()
        return d.quantize(Decimal("0.01"))
    except (ValueError, InvalidOperation, TypeError):
        frappe.throw("A valid money amount is required.")


def _setup_checks():
    problems = []
    if not frappe.db.exists("Company", COMPANY):
        problems.append("Shop company is not configured")
    if not frappe.db.exists("Warehouse", WAREHOUSE):
        problems.append("Retail warehouse is missing")
    else:
        wh = frappe.db.get_value("Warehouse", WAREHOUSE,
            ["company", "is_group", "disabled"], as_dict=True)
        if wh.company != COMPANY or wh.is_group or wh.disabled:
            problems.append("Retail warehouse is not active for this company")
    if not frappe.db.exists("Price List", PRICE_LIST):
        problems.append("Standard selling price list is missing")
    else:
        pl = frappe.db.get_value("Price List", PRICE_LIST,
            ["selling", "enabled", "currency"], as_dict=True)
        if not pl.selling or not pl.enabled or pl.currency != "BDT":
            problems.append("Selling price list must be active and use BDT")
    if not frappe.db.exists("Account", CASH_ACCOUNT):
        problems.append("Cash ledger is missing")
    else:
        acc = frappe.db.get_value("Account", CASH_ACCOUNT,
            ["company", "is_group", "account_type", "account_currency", "disabled"],
            as_dict=True)
        if (acc.company != COMPANY or acc.is_group or acc.disabled
                or acc.account_type != "Cash" or acc.account_currency != "BDT"):
            problems.append("Cash account must be an active BDT Cash ledger for this company")
    if not frappe.db.exists("Mode of Payment", "Cash"):
        problems.append("Cash payment mode is missing")
    if not frappe.get_meta("Sales Invoice").has_field(FIELD):
        problems.append("Checkout idempotency field missing; run installation setup")
    return problems


def setup():
    """Create only a unique checkout ID field. No invoices or stock movements."""
    if not frappe.db.exists("Company", COMPANY):
        frappe.throw("Expected company missing: " + COMPANY)
    existing = frappe.get_meta("Sales Invoice").get_field(FIELD)
    if existing:
        if existing.fieldtype != "Data" or not existing.unique:
            frappe.throw("Existing checkout key field is incompatible; no change made")
        return {"ok": True, "field": FIELD, "created": False}
    frappe.get_doc({
        "doctype": "Custom Field", "dt": "Sales Invoice", "fieldname": FIELD,
        "label": "SERVICING OS Counter Key", "fieldtype": "Data",
        "unique": 1, "hidden": 1, "read_only": 1, "no_copy": 1,
    }).insert(ignore_permissions=True)
    frappe.clear_cache(doctype="Sales Invoice")
    return {"ok": True, "field": FIELD, "created": True}


def _price(item_code, uom):
    rows = frappe.get_all("Item Price",
        filters={"item_code": item_code, "price_list": PRICE_LIST, "selling": 1},
        fields=["price_list_rate", "currency", "uom", "valid_from", "valid_upto"],
        order_by="modified desc", limit_page_length=100)
    today = getdate(nowdate())
    for r in rows:
        if r.currency != "BDT" or (r.uom and r.uom != uom):
            continue
        if r.valid_from and getdate(r.valid_from) > today:
            continue
        if r.valid_upto and getdate(r.valid_upto) < today:
            continue
        rate = _money(r.price_list_rate)
        if rate > 0:
            return rate
    return None


def _stock(item_code):
    d = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": WAREHOUSE},
                            ["actual_qty", "reserved_qty"], as_dict=True)
    # This is a preliminary availability check; ERP validates at submission.
    return flt(d.actual_qty) if d else 0


def _catalog_rows(search="", limit=60):
    _require("Item", "read")
    search = str(search or "").strip()[:100]
    limit = max(1, min(int(limit or 60), 100))
    filters = {"disabled": 0, "is_sales_item": 1, "is_stock_item": 1,
               "has_serial_no": 0, "has_batch_no": 0}
    opts = dict(filters=filters,
        fields=["name", "item_name", "stock_uom", "item_group"],
        order_by="item_name asc", limit_page_length=limit)
    if search:
        escaped = search.replace("%", r"\%").replace("_", r"\_")
        opts["or_filters"] = [
            ["Item", "name", "like", f"%{escaped}%"],
            ["Item", "item_name", "like", f"%{escaped}%"],
        ]
        barcode = frappe.db.get_value("Item Barcode", {"barcode": search}, "parent")
        if barcode:
            opts["or_filters"].append(["Item", "name", "=", barcode])
    result = []
    for row in frappe.get_list("Item", **opts):
        rate = _price(row.name, row.stock_uom)
        result.append({"item_code": row.name, "item_name": row.item_name,
            "uom": row.stock_uom, "group": row.item_group,
            "stock_qty": _stock(row.name),
            "rate": float(rate) if rate is not None else None})
    return result


@frappe.whitelist(methods=["GET"])
def get_register(search="", customer_search=""):
    _require("Customer", "read")
    customers_query = {"fields": ["name", "customer_name"],
        "filters": {"disabled": 0}, "order_by": "customer_name asc",
        "limit_page_length": 40}
    if customer_search:
        s = str(customer_search).strip()[:100]
        escaped = s.replace("%", r"\%").replace("_", r"\_")
        customers_query["or_filters"] = [
            ["Customer", "name", "like", f"%{escaped}%"],
            ["Customer", "customer_name", "like", f"%{escaped}%"]]
    customers = [dict(x) for x in frappe.get_list("Customer", **customers_query)]
    perms = {d: {p: bool(frappe.has_permission(d, ptype=p))
                 for p in ("create", "submit")} for d in ("Sales Invoice", "Payment Entry")}
    problems = _setup_checks()
    if not customers:
        problems.append("Select or create a customer before checkout")
    if not all(perms[d][p] for d in perms for p in perms[d]):
        problems.append("Current cashier needs Sales Invoice and Payment Entry create/submit rights")
    return {"company": COMPANY, "currency": "BDT", "warehouse": WAREHOUSE,
        "items": _catalog_rows(search), "customers": customers,
        "ready": not problems, "checks": problems, "permissions": perms,
        "cash_only": True, "pos_profile_required": False,
        "note": "Only products with stock and selling prices can be checked out."}


def _prepare(customer, items, key=None):
    for dt in ("Customer", "Item"):
        _require(dt, "read")
    problems = _setup_checks()
    if problems:
        frappe.throw("Counter setup incomplete: " + "; ".join(problems))
    if not customer or not frappe.db.exists("Customer", customer):
        frappe.throw("Select an existing customer.")
    cust = frappe.db.get_value("Customer", customer, ["disabled"], as_dict=True)
    if cust and cust.disabled:
        frappe.throw("Customer is disabled.")
    if isinstance(items, str):
        items = frappe.parse_json(items)
    if not isinstance(items, list) or not 1 <= len(items) <= 40:
        frappe.throw("A sale must have 1–40 product lines.")
    qty_by_code = {}
    for row in items:
        if not isinstance(row, dict):
            frappe.throw("Invalid product row")
        code = str(row.get("item_code") or "")
        try:
            qty = Decimal(str(row.get("qty")))
        except (ValueError, TypeError, InvalidOperation):
            frappe.throw("Invalid quantity")
        if not qty.is_finite() or qty != qty.to_integral_value() or qty < 1 or qty > 1000:
            frappe.throw("Quantity must be 1–1000 whole units")
        qty_by_code[code] = qty_by_code.get(code, Decimal(0)) + qty
    if len(qty_by_code) > 40:
        frappe.throw("Too many distinct products")
    lines = []
    for code, qty in qty_by_code.items():
        if not frappe.db.exists("Item", code):
            frappe.throw("Unknown Item " + code)
        it = frappe.db.get_value("Item", code,
            ["item_name", "disabled", "is_sales_item", "is_stock_item",
             "has_serial_no", "has_batch_no", "stock_uom"], as_dict=True)
        if (it.disabled or not it.is_sales_item or not it.is_stock_item
                or it.has_serial_no or it.has_batch_no):
            frappe.throw("This counter currently supports standard stock products only: " + code)
        price = _price(code, it.stock_uom)
        if price is None:
            frappe.throw("Selling price not configured for: " + code)
        if Decimal(str(_stock(code))) < qty:
            frappe.throw(f"Insufficient stock in {WAREHOUSE}: {code} (requested {qty})")
        lines.append({"item_code": code, "item_name": it.item_name,
            "qty": int(qty), "uom": it.stock_uom,
            "rate": float(price), "warehouse": WAREHOUSE,
            "conversion_factor": 1})
    inv = frappe.get_doc({
        "doctype": "Sales Invoice", "company": COMPANY, "customer": customer,
        "selling_price_list": PRICE_LIST, "set_warehouse": WAREHOUSE,
        "currency": "BDT", "update_stock": 1, "is_pos": 0,
        "ignore_pricing_rule": 1, "items": lines,
    })
    if key:
        inv.set(FIELD, key)
    inv.run_method("set_missing_values")
    inv.run_method("calculate_taxes_and_totals")
    if not inv.update_stock or inv.company != COMPANY or inv.customer != customer:
        frappe.throw("Invoice defaults changed critical checkout values")
    for original, computed in zip(lines, inv.items):
        if _money(computed.rate) != _money(original["rate"]):
            frappe.throw("Item rates were altered by another pricing setting. Checkout stopped.")
        if computed.warehouse != WAREHOUSE:
            frappe.throw("Invoice warehouse changed unexpectedly")
    if _money(inv.grand_total) <= 0:
        frappe.throw("Calculated invoice total is invalid")
    return inv


@frappe.whitelist(methods=["POST"])
def quote_sale(customer, items):
    inv = _prepare(customer, items)
    return {"company": COMPANY, "customer": customer,
        "net_total": float(_money(inv.net_total)),
        "tax_total": float(_money(inv.total_taxes_and_charges)),
        "grand_total": float(_money(inv.grand_total)),
        "currency": "BDT", "items": [{"item_code": i.item_code,
            "item_name": i.item_name, "qty": i.qty,
            "rate": i.rate, "amount": i.amount} for i in inv.items],
        "message": "Final checkout recalculates prices, tax, and stock."}


@frappe.whitelist(methods=["POST"])
def complete_cash_sale(customer, items, checkout_key, expected_total):
    """All-or-nothing invoice+cash receipt on a single Frappe POST request.

    In case of a validation failure, Frappe rolls the transaction back.
    A unique invoice field prevents accidental duplicate checkout keys.
    """
    _require("Sales Invoice", "create")
    _require("Sales Invoice", "submit")
    _require("Payment Entry", "create")
    _require("Payment Entry", "submit")
    key = str(checkout_key or "").strip()
    if not re.fullmatch(r"[a-zA-Z0-9_-]{16,64}", key):
        frappe.throw("Invalid checkout reference")
    existing = frappe.db.get_value("Sales Invoice", {FIELD: key},
        ["name", "docstatus", "customer", "grand_total"], as_dict=True)
    if existing:
        if existing.docstatus == 1:
            return {"success": True, "already_processed": True,
                "invoice": existing.name, "total": flt(existing.grand_total)}
        frappe.throw("This checkout reference belongs to an incomplete or cancelled invoice")
    inv = _prepare(customer, items, key=key)
    if abs(_money(inv.grand_total) - _money(expected_total)) > Decimal("0.01"):
        frappe.throw("Total changed since review. Refresh the quote before collecting cash.")
    # All operations use the normal current transaction. No ignore_permissions.
    # A failure submitting the allocated Payment Entry causes invoice/stock rollback.
    inv.insert()
    if abs(_money(inv.grand_total) - _money(expected_total)) > Decimal("0.01"):
        frappe.throw("Invoice total changed during validation; sale was not posted")
    inv.submit()
    if inv.docstatus != 1 or inv.update_stock != 1:
        frappe.throw("Sales posting not confirmed")
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    amount = flt(inv.outstanding_amount)
    if amount <= 0:
        frappe.throw("Invoice has no outstanding cash amount; payment mode unexpected")
    payment = get_payment_entry("Sales Invoice", inv.name,
        bank_account=CASH_ACCOUNT, bank_amount=amount)
    if (payment.payment_type != "Receive" or payment.party_type != "Customer"
            or payment.party != customer or payment.company != COMPANY):
        frappe.throw("Unexpected payment mapping")
    payment.mode_of_payment = "Cash"
    payment.paid_to = CASH_ACCOUNT
    payment.paid_amount = amount
    payment.received_amount = amount
    refs = [r for r in payment.references if
            r.reference_doctype == "Sales Invoice" and r.reference_name == inv.name]
    if len(payment.references) != 1 or len(refs) != 1:
        frappe.throw("Unexpected payment allocations; sale not completed")
    refs[0].allocated_amount = amount
    payment.insert()
    payment.submit()
    if payment.docstatus != 1 or payment.paid_to != CASH_ACCOUNT:
        frappe.throw("Cash payment was not confirmed")
    inv.reload()
    return {"success": True, "already_processed": False,
        "invoice": inv.name, "payment_entry": payment.name,
        "company": COMPANY, "customer": customer,
        "total": float(_money(inv.grand_total)),
        "outstanding": float(_money(inv.outstanding_amount)),
        "items": [{"item_code": r.item_code, "item_name": r.item_name,
            "qty": r.qty, "rate": r.rate, "amount": r.amount} for r in inv.items]}


@frappe.whitelist(methods=["GET"])
def recent_sales():
    _require("Sales Invoice", "read")
    return {"sales": [dict(d) for d in frappe.get_list(
        "Sales Invoice", filters={"company": COMPANY, "docstatus": 1,
                                FIELD: ["is", "set"]},
        fields=["name", "customer", "customer_name", "posting_date",
                "grand_total", "outstanding_amount"],
        order_by="creation desc", limit_page_length=12)]}
