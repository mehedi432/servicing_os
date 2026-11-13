import frappe

COMPANY = "AL MODINA COMPUTERS LIMITED"
PROFILE = "AMCL Retail Counter"
WAREHOUSE = "Stores - AMCL"
PRICE_LIST = "Standard Selling"
CURRENCY = "BDT"
CASH_ACCOUNT = "Cash - AMCL"


def _require(condition, message):
    if not condition:
        frappe.throw(message)


def _account(name, root_type=None, account_type=None):
    rec = frappe.db.get_value(
        "Account", name,
        ["company", "root_type", "account_type", "is_group", "disabled"],
        as_dict=True,
    )
    _require(rec and rec.company == COMPANY and not rec.is_group and not rec.disabled,
             "Missing or inactive leaf Account: " + name)
    if root_type:
        _require(rec.root_type == root_type, "Incorrect account root type: " + name)
    if account_type:
        _require(rec.account_type == account_type, "Incorrect account type: " + name)
    return name


def _write_off_account():
    accounts = frappe.get_all(
        "Account",
        filters={"company": COMPANY, "is_group": 0, "disabled": 0, "root_type": "Expense"},
        pluck="name", limit_page_length=500,
    )
    explicit = ["Write Off - AMCL", "Write Off Account - AMCL", "Write Off Expenses - AMCL"]
    candidates = [x for x in explicit if x in accounts]
    if not candidates:
        candidates = [x for x in accounts if "write" in x.lower() and "off" in x.lower()]
    _require(len(candidates) == 1,
             "Cannot safely select a write-off expense account. "
             "Open ERPNext > Chart of Accounts, configure a dedicated leaf Write Off account "
             "for AMCL, then rerun. Expense account candidates: " + ", ".join(accounts[:25]))
    return candidates[0]


def _cost_center():
    centers = frappe.get_all(
        "Cost Center", filters={"company": COMPANY, "is_group": 0, "disabled": 0},
        pluck="name", limit_page_length=200,
    )
    preferred = [x for x in ["Main - AMCL", "AMCL - AMCL"] if x in centers]
    if len(preferred) == 1:
        return preferred[0]
    _require(len(centers) == 1,
             "Cannot safely choose a POS write-off cost center. "
             "Set one explicitly in ERPNext POS Profile. Available: " + ", ".join(centers[:25]))
    return centers[0]


def setup():
    # Standard ERPNext master data only; there is no custom POS DocType.
    _require(frappe.db.exists("Company", COMPANY), "Company not found: " + COMPANY)
    _require(frappe.db.get_value("Company", COMPANY, "default_currency") == CURRENCY,
             "AMCL currency is not BDT; stopped.")

    wh = frappe.db.get_value(
        "Warehouse", WAREHOUSE, ["company", "is_group", "disabled"], as_dict=True)
    _require(wh and wh.company == COMPANY and not wh.is_group and not wh.disabled,
             "Invalid or disabled POS warehouse: " + WAREHOUSE)

    price = frappe.db.get_value(
        "Price List", PRICE_LIST,
        ["currency", "selling", "enabled"], as_dict=True,
    )
    _require(price and price.currency == CURRENCY and price.selling and price.enabled,
             "Standard Selling is not an active BDT selling Price List.")

    _account(CASH_ACCOUNT, account_type="Cash")
    _account("Sales - AMCL", root_type="Income")
    _account("Cost of Goods Sold - AMCL", root_type="Expense")
    write_off = _write_off_account()
    cost_center = _cost_center()

    _require(frappe.db.exists("Mode of Payment", "Cash"), "Cash Mode of Payment is missing.")
    mop = frappe.get_doc("Mode of Payment", "Cash")
    _require(mop.enabled, "Cash Mode of Payment is disabled.")
    _require(mop.type == "Cash", "Cash Mode of Payment has an unexpected type.")
    existing_maps = [row for row in mop.get("accounts", []) if row.company == COMPANY]
    _require(len(existing_maps) <= 1, "Duplicate AMCL mapping in Cash Mode of Payment.")
    if existing_maps:
        _require(existing_maps[0].default_account == CASH_ACCOUNT,
                 "Cash payment mode already maps AMCL to "
                 + str(existing_maps[0].default_account)
                 + "; not overwriting financial settings.")

    if frappe.db.exists("POS Profile", PROFILE):
        record = frappe.get_doc("POS Profile", PROFILE)
        _require(record.company == COMPANY, "Existing profile belongs to another company.")
        return {
            "action": "already_exists_no_changes",
            "profile": record.name,
            "company": record.company,
            "disabled": record.disabled,
            "warehouse": record.warehouse,
            "message": "Review its payment methods and applicable users in ERPNext Desk.",
        }

    other = frappe.get_all("POS Profile", filters={"company": COMPANY}, pluck="name")
    _require(not other, "AMCL already has POS Profile(s): " + ", ".join(other) +
             ". Review these instead of creating duplicates.")

    # Do not select a named customer's account as Walk-In.
    # If a dedicated customer already exists, use it; otherwise POS will ask for one.
    customer = frappe.db.exists("Customer", {"customer_name": "AMCL Walk-in Customer"})

    # Set the payment account mapping only if genuinely missing.
    mapped = False
    if not existing_maps:
        mop.append("accounts", {"company": COMPANY, "default_account": CASH_ACCOUNT})
        mop.save(ignore_permissions=True)
        mapped = True

    doc = frappe.get_doc({
        "doctype": "POS Profile",
        "name": PROFILE,
        "company": COMPANY,
        "currency": CURRENCY,
        "warehouse": WAREHOUSE,
        "selling_price_list": PRICE_LIST,
        "disabled": 0,
        "write_off_account": write_off,
        "write_off_cost_center": cost_center,
        "write_off_limit": 0,
        "income_account": "Sales - AMCL",
        "expense_account": "Cost of Goods Sold - AMCL",
        "print_receipt_on_order_complete": 1,
        "hide_unavailable_items": 0,
        "validate_stock_on_save": 1,
        "allow_rate_change": 0,
        "allow_discount_change": 0,
        "payments": [{"mode_of_payment": "Cash", "default": 1}],
        # Do not restrict to Administrator: existing Sales Users should be able to use it.
    })
    if customer:
        doc.customer = customer
    doc.insert(ignore_permissions=True)
    return {
        "action": "created",
        "profile": doc.name,
        "company": COMPANY,
        "warehouse": WAREHOUSE,
        "selling_price_list": PRICE_LIST,
        "payment": "Cash -> " + CASH_ACCOUNT,
        "cash_mapping_added": mapped,
        "customer": customer or None,
        "write_off_account": write_off,
        "write_off_cost_center": cost_center,
        "financial_transactions_created": 0,
        "note": "Select a customer and open a POS Opening Entry before checkout. No actual stock yet.",
    }
