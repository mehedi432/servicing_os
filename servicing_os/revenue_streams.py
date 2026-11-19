"""Company-specific ERPNext income accounts for SERVICING OS invoices."""
from collections import defaultdict

import frappe

from servicing_os.api.service_invoice_661 import LINK_FIELDS

STREAM_FIELD = "custom_sos_revenue_stream"
REPORT_STREAM_FIELD = "custom_sos_reporting_stream"
USED_MARKERS = ("custom_sos_ul_item", "custom_sos_ul_checkout_key")
RETAIL_MARKER = "custom_servicing_counter_key"
SOURCE_FIELDS = (*LINK_FIELDS, *USED_MARKERS, RETAIL_MARKER, "remarks")
STREAMS = {
    "Servicing": ("custom_sos_servicing_income_account", "Servicing Income"),
    "Retail Stock": ("custom_sos_retail_income_account", "Retail Stock Sales"),
    "Used Laptops": ("custom_sos_used_income_account", "Used Laptop Sales"),
}
KIND_TO_STREAM = {"service": "Servicing", "retail": "Retail Stock", "used": "Used Laptops"}
SECTION = "custom_sos_revenue_accounts_section"


def _definitions():
    account_fields = [
        {"fieldname": SECTION, "label": "SERVICING OS Revenue Accounts",
         "fieldtype": "Section Break", "insert_after": "default_income_account"}
    ]
    for field, label in STREAMS.values():
        account_fields.append({"fieldname": field, "label": label + " Account",
                               "fieldtype": "Link", "options": "Account",
                               "insert_after": account_fields[-1]["fieldname"]})
    return {
        "Company": account_fields,
        "Sales Invoice": [
            {"fieldname": STREAM_FIELD, "label": "Revenue Stream", "fieldtype": "Select",
             "options": "\n" + "\n".join(STREAMS), "insert_after": "customer",
             "read_only": 1, "in_standard_filter": 1, "search_index": 1,
             "print_hide": 1},
            {"fieldname": REPORT_STREAM_FIELD, "label": "Historical Reporting Stream",
             "fieldtype": "Select", "options": "\n" + "\n".join(STREAMS),
             "insert_after": STREAM_FIELD, "read_only": 1, "no_copy": 1, "print_hide": 1,
             "description": "Used for Counter invoice reporting. Does not change the posted income account."},
        ],
    }


def _check_field(meta, expected):
    name = expected["fieldname"]
    field = meta.get_field(name)
    if field and (field.fieldtype != expected["fieldtype"]
                  or ("options" in expected and field.options != expected["options"])
                  or ("read_only" in expected and not field.read_only)):
        frappe.throw(f"{meta.name}.{name} conflicts with the SERVICING OS revenue configuration.")
    return field


def ensure_schema():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    for doctype, fields in _definitions().items():
        meta = frappe.get_meta(doctype, cached=False)
        missing = [field for field in fields if not _check_field(meta, field)]
        if missing:
            create_custom_fields({doctype: missing}, update=False)
        frappe.clear_cache(doctype=doctype)
        if any(field["fieldtype"] != "Section Break" and not frappe.db.has_column(doctype, field["fieldname"])
               for field in fields):
            frappe.db.updatedb(doctype)
    return verify_schema()


def verify_schema():
    for doctype, fields in _definitions().items():
        meta = frappe.get_meta(doctype, cached=False)
        for field in fields:
            name = field["fieldname"]
            if not _check_field(meta, field) or (
                field["fieldtype"] != "Section Break" and not frappe.db.has_column(doctype, name)
            ):
                frappe.throw(f"Missing {doctype}.{name}. Run bench migrate.")
    return {"status": "OK", "revenue_streams": list(STREAMS)}


def _account_details(account):
    if not account:
        return None
    fields = ["company", "root_type", "is_group", "disabled", "account_currency"]
    if frappe.get_meta("Account").has_field("freeze_account"):
        fields.append("freeze_account")
    return frappe.db.get_value("Account", account, fields, as_dict=True)


def _valid_account(account, company, currency, *, group=False):
    row = _account_details(account)
    return bool(row and row.get("company") == company and row.get("root_type") == "Income"
                and bool(row.get("is_group")) == group and not row.get("disabled")
                and row.get("freeze_account") != "Yes"
                and (group or row.get("account_currency") == currency))


def validate_company_accounts(doc, method=None):
    selected = [doc.get(field) for field, _ in STREAMS.values() if doc.get(field)]
    if len(selected) != len(set(selected)):
        frappe.throw("Choose a different Income account for each SERVICING OS revenue stream.")
    for account in selected:
        if not _valid_account(account, doc.name, doc.default_currency):
            frappe.throw(f"{account} must be an active Income ledger for {doc.name} in {doc.default_currency}.")


def _active_company():
    companies = set(frappe.get_all("Servicing Shop", filters={"is_active": 1},
                                   pluck="company", limit_page_length=0))
    companies.discard(None)
    companies.discard("")
    if len(companies) != 1:
        frappe.throw("Configure an active Servicing Shop or pass the Company name explicitly.")
    return next(iter(companies))


def _income_parent(company, requested=None):
    parent = requested
    if not parent and company.default_income_account:
        parent = frappe.db.get_value("Account", company.default_income_account, "parent_account")
    if not parent:
        roots = frappe.get_all("Account", filters={"company": company.name, "root_type": "Income",
                                                   "is_group": 1, "disabled": 0,
                                                   "parent_account": ["is", "not set"]},
                               pluck="name", limit_page_length=2)
        if len(roots) == 1:
            parent = roots[0]
    if not _valid_account(parent, company.name, company.default_currency, group=True):
        frappe.throw("Pass an active Income group for this Company as parent_account.")
    return parent


def setup_income_accounts(company=None, parent_account=None):
    """Bench command. Create or reuse income ledgers for a Company's blank mappings."""
    frappe.only_for("System Manager")
    verify_schema()
    company = company or _active_company()
    if not frappe.db.exists("Company", company):
        frappe.throw(f"Company {company} does not exist.")
    frappe.db.sql("SELECT name FROM `tabCompany` WHERE name = %s FOR UPDATE", (company,))
    doc = frappe.get_doc("Company", company)
    doc.check_permission("write")
    validate_company_accounts(doc)
    parent = None
    created = []
    changed = False
    for field, account_name in STREAMS.values():
        if doc.get(field):
            continue
        matches = frappe.get_all("Account", filters={"company": company, "account_name": account_name},
                                 pluck="name", limit_page_length=2)
        if len(matches) > 1:
            frappe.throw(f"Multiple accounts are named {account_name}. Select a ledger on the Company.")
        if matches:
            account = matches[0]
            if not _valid_account(account, company, doc.default_currency):
                frappe.throw(f"{account} exists but is unsuitable. Select a valid ledger on the Company.")
        else:
            if not parent:
                parent = _income_parent(doc, parent_account)
            ledger = frappe.get_doc({"doctype": "Account", "company": company, "account_name": account_name,
                                     "parent_account": parent, "is_group": 0,
                                     "account_currency": doc.default_currency})
            ledger.insert()
            account = ledger.name
            created.append(account)
        doc.set(field, account)
        changed = True
    validate_company_accounts(doc)
    if changed:
        doc.save()
    return {"company": company, "accounts": {stream: doc.get(field) for stream, (field, _) in STREAMS.items()},
            "created_accounts": created}


def invoice_source_stream(doc):
    if any(doc.get(field) for field in LINK_FIELDS):
        return "Servicing"
    if any(doc.get(field) for field in USED_MARKERS):
        return "Used Laptops"
    if doc.get(RETAIL_MARKER):
        return "Retail Stock"
    parts = str(doc.get("remarks") or "").split(" | ", 2)
    if len(parts) > 1 and parts[0] == "SERVICING OS":
        return {"SERVICE JOB": "Servicing", "RETAIL SALE": "Retail Stock",
                "USED LAPTOP": "Used Laptops"}.get(parts[1])
    return None


def _classify(doc):
    if any(doc.get(field) for field in LINK_FIELDS):
        return "Servicing"
    if any(doc.get(field) for field in USED_MARKERS):
        return "Used Laptops"
    tag = doc.get(STREAM_FIELD)
    return tag if tag in STREAMS else invoice_source_stream(doc)


def _apply_return(doc, source, stream):
    original_stream = source.get(STREAM_FIELD)
    if original_stream in STREAMS:
        doc.set(STREAM_FIELD, original_stream)
    elif stream and doc.get(STREAM_FIELD):
        doc.set(STREAM_FIELD, None)
    if not stream and not _classify(source):
        return
    rows_by_name = {row.name: row for row in source.items}
    accounts_by_item = defaultdict(set)
    for row in source.items:
        if row.income_account:
            accounts_by_item[row.item_code].add(row.income_account)
    for row in doc.items:
        reference = rows_by_name.get(row.get("sales_invoice_item"))
        if reference and reference.item_code == row.item_code and reference.income_account:
            row.income_account = reference.income_account
        else:
            accounts = accounts_by_item[row.item_code]
            if len(accounts) == 1:
                row.income_account = next(iter(accounts))
            elif row.income_account not in accounts:
                frappe.throw(f"Match the credit note item {row.item_code} to its original invoice income account.")


def apply_invoice_income(doc, method=None):
    """Run before native validation and posting, without touching stock or payments."""
    stream = _classify(doc)
    if doc.get("is_return") and doc.get("return_against"):
        source = frappe.get_doc("Sales Invoice", doc.return_against)
        if source.company == doc.company:
            _apply_return(doc, source, stream)
        return
    if not stream or not doc.company or not doc.items:
        return
    field, _ = STREAMS[stream]
    if not frappe.get_meta("Company").has_field(field) or not frappe.get_meta("Sales Invoice").has_field(STREAM_FIELD):
        frappe.throw("Run bench migrate to install the SERVICING OS revenue fields.")
    currency = frappe.db.get_value("Company", doc.company, "default_currency")
    mappings = frappe.db.get_value("Company", doc.company,
                                   [name for name, _ in STREAMS.values()], as_dict=True) or {}
    account = mappings.get(field)
    if not account:
        frappe.throw(f"Set the {stream} Income Account on Company {doc.company} under SERVICING OS Revenue Accounts.")
    if list(mappings.values()).count(account) != 1:
        frappe.throw("Choose a different Income account for each SERVICING OS revenue stream.")
    if not _valid_account(account, doc.company, currency):
        frappe.throw(f"The {stream} Income Account must be an active Income ledger for {doc.company} in {currency}.")
    doc.set(STREAM_FIELD, stream)
    for row in doc.items:
        row.income_account = account
