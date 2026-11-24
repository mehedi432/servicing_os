"""SERVICING OS — ERPNext native retail sales history (read-only).

POS Invoice and Sales Invoice are deliberately reported separately. POS Invoice
can be a session sub-ledger that is consolidated into a Sales Invoice on close.
Neither creating nor reading this module posts stock, payments or GL entries.
"""
from datetime import datetime
import frappe
from frappe.utils import add_days, nowdate, flt
from servicing_os.api.site_company_706 import current_company



def _fields(doctype):
    return {f.fieldname for f in frappe.get_meta(doctype).fields} | {"name", "owner", "docstatus"}


def _date(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError):
        frappe.throw("Dates must use YYYY-MM-DD format.")


def _is_retail_sales_invoice(row):
    return bool(row.get("is_pos") or row.get("is_created_using_pos") or row.get("pos_profile"))


def _record(row, doctype):
    val = dict(row)
    currency = val.get("currency") or "BDT"
    return {
        "doctype": doctype,
        "name": val.get("name"),
        "posting_date": str(val.get("posting_date") or ""),
        "customer": val.get("customer"),
        "customer_name": val.get("customer_name") or val.get("customer"),
        "cashier": val.get("owner"),  # creator; not guaranteed cashier/closing user
        "pos_profile": val.get("pos_profile"),
        "grand_total": flt(val.get("grand_total")),
        "outstanding_amount": (flt(val.get("outstanding_amount")) if doctype == "Sales Invoice" else None),
        "currency": currency,
        "is_return": bool(val.get("is_return")),
        "status": val.get("status") or ("POS Ticket" if doctype == "POS Invoice" else "Submitted"),
        "posting_basis": ("POS ticket — confirm session closing" if doctype == "POS Invoice" else "Submitted Sales Invoice"),
    }


@frappe.whitelist(methods=["GET"])
def get_retail_history(from_date=None, to_date=None, search="", doc_type="all", cashier="", pos_profile="", limit=150):
    """Permission-aware retail ticket history, never a combined revenue figure."""
    start = _date(from_date, add_days(nowdate(), -30))
    end = _date(to_date, nowdate())
    if start > end:
        frappe.throw("From Date cannot be later than To Date.")
    if doc_type not in ("all", "POS Invoice", "Sales Invoice"):
        frappe.throw("Invalid document type filter.")
    search = str(search or "").strip().casefold()[:100]
    cashier = str(cashier or "").strip().casefold()[:100]
    pos_profile = str(pos_profile or "").strip()[:140]
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 150
    limit = max(1, min(250, limit))
    results = []
    unavailable = []
    possible_truncation = False
    scan_limit = 800

    types = ["POS Invoice", "Sales Invoice"] if doc_type == "all" else [doc_type]
    for dt in types:
        if not frappe.db.exists("DocType", dt):
            unavailable.append(dt + " does not exist on this site")
            continue
        if not frappe.has_permission(dt, "read"):
            unavailable.append("Your user does not have permission to read " + dt)
            continue
        available = _fields(dt)
        columns = [c for c in (
            "name", "posting_date", "customer", "customer_name", "owner", "pos_profile",
            "grand_total", "currency", "is_return", "status", "outstanding_amount",
            "is_pos", "is_created_using_pos", "is_consolidated"
        ) if c in available]
        filters = {"company": current_company(), "docstatus": 1, "posting_date": ["between", [start, end]]}
        if pos_profile and "pos_profile" in available:
            filters["pos_profile"] = pos_profile
        elif pos_profile:
            continue
        if cashier:
            # Filter later, because the field is named owner, not guaranteed a cashier.
            pass
        # Applying read permission via frappe.get_list, not frappe.get_all.
        rows = frappe.get_list(
            dt, fields=columns, filters=filters,
            order_by="posting_date desc, name desc", limit_page_length=scan_limit,
        )
        if len(rows) == scan_limit:
            possible_truncation = True
        for row in rows:
            val = dict(row)
            if dt == "Sales Invoice":
                # Ignore consolidated summaries: when POS Invoice is used, that
                # summary would double-count individual tickets.
                if val.get("is_consolidated"):
                    continue
                if not _is_retail_sales_invoice(val):
                    continue
            if cashier and cashier not in str(val.get("owner") or "").casefold():
                continue
            if search and not any(search in str(val.get(f) or "").casefold()
                                  for f in ("name", "customer", "customer_name", "pos_profile")):
                continue
            results.append(_record(val, dt))

    results.sort(key=lambda x: (x["posting_date"], x["name"]), reverse=True)
    if len(results) > limit:
        possible_truncation = True
    results = results[:limit]
    tickets = [r for r in results if r["doctype"] == "POS Invoice"]
    posted = [r for r in results if r["doctype"] == "Sales Invoice"]
    excluded_currencies = len([r for r in results if r["currency"] != "BDT"])
    return {
        "company": current_company(),
        "currency": "BDT",
        "from_date": start,
        "to_date": end,
        "rows": results,
        "shown": len(results),
        "has_more": possible_truncation,
        "totals": {
            "pos_tickets_bdt": round(sum(r["grand_total"] for r in tickets if r["currency"] == "BDT"), 2),
            "posted_retail_invoices_bdt": round(sum(r["grand_total"] for r in posted if r["currency"] == "BDT"), 2),
            "pos_ticket_count": len(tickets),
            "sales_invoice_count": len(posted),
            "other_currency_rows_excluded": excluded_currencies,
        },
        "warnings": unavailable,
        "note": "Do not add POS ticket totals to Sales Invoice totals. POS tickets may be consolidated into a Sales Invoice at session close. Amounts are document totals, not daily cash collections.",
    }


@frappe.whitelist(methods=["GET"])
def get_retail_sale_detail(doctype, name):
    """Read-only details from the ERPNext original document, no print bypass."""
    if doctype not in ("POS Invoice", "Sales Invoice"):
        frappe.throw("Only retail POS and Sales Invoices are supported.")
    doc = frappe.get_doc(doctype, name)
    doc.check_permission("read")
    if doc.company != current_company() or doc.docstatus != 1:
        frappe.throw("This is not a submitted AMCL retail document.")
    if doctype == "Sales Invoice" and (
        doc.get("is_consolidated") or not _is_retail_sales_invoice(doc)
    ):
        frappe.throw("This is not an individual retail Sales Invoice.")
    from servicing_os.invoice_printing import (
        invoice_serial_numbers, invoice_document_print_amounts, invoice_payment_schedule,
    )

    items = doc.get("items") or []
    serials = invoice_serial_numbers(doc, items)
    currency = doc.get("currency") or "BDT"
    return {
        **invoice_document_print_amounts(doc, currency),
        "net_total": flt(doc.get("net_total")),
        "discount_amount": flt(doc.get("discount_amount")),
        "additional_discount_percentage": flt(doc.get("additional_discount_percentage")),
        "total_taxes_and_charges": flt(doc.get("total_taxes_and_charges")),
        "outstanding_amount": flt(doc.get("outstanding_amount")),
        "payment_schedule": invoice_payment_schedule(doc),
        "docstatus": doc.docstatus,
        "company": doc.company,
        "due_date": str(doc.get("due_date") or ""),
        "doctype": doctype,
        "name": doc.name,
        "customer": doc.get("customer_name") or doc.get("customer"),
        "posting_date": str(doc.get("posting_date") or ""),
        "grand_total": flt(doc.get("grand_total")),
        "currency": currency,
        "items": [
            {"code": x.get("item_code"), "description": x.get("item_name"),
             "qty": flt(x.get("qty")), "rate": flt(x.get("rate")),
             "amount": flt(x.get("amount")),
             "serial_no": serials.get(x.name) or x.get("serial_no") or ""}
            for x in items
        ],
        "note": "Print uses the original ERPNext document and its configured Print Format.",
    }
