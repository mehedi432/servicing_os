"""Warranty lookup and native claims for the active inventory company."""

from html import escape

import frappe
from frappe.utils import add_days, getdate, now_datetime, strip_html, today

from servicing_os.api.inventory_workspace import _company
from servicing_os.api.warranty_serials import voucher_serials
from servicing_os.api.invoice_warranty_659 import ALLOWED, _child_meta, _details
from servicing_os.warranty_schema import CLAIM_FIELDS

CLAIM = "Warranty Claim"
CLAIM_STATES = ("Open", "Work In Progress", "Closed", "Cancelled")
PAGE_SIZE = 20


def _require(doctype, action="read"):
    if not frappe.has_permission(doctype, action):
        frappe.throw(f"{doctype} {action} permission is required.", frappe.PermissionError)


def _reference(value, label):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 140:
        frappe.throw(f"Enter a valid {label}.")
    return value.strip()


def _term(value):
    return str(value or "").strip()[:140].replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def _page(value):
    try:
        return max(1, min(int(value or 1), 10000))
    except (ValueError, TypeError):
        return 1


def _sale(doctype, name, company):
    if doctype not in ALLOWED:
        frappe.throw("Unsupported invoice type.")
    _require(doctype)
    sale = frappe.get_doc(doctype, name)
    sale.check_permission("read")
    if sale.company != company or sale.docstatus != 1 or sale.get("is_return"):
        frappe.throw("Choose a submitted sales invoice for the active shop.")
    return sale


def _serials(value):
    return list(dict.fromkeys(line.strip() for line in str(value or "").splitlines() if line.strip()))


def _coverage(terms, posting_date, as_of):
    start = terms["warranty_start_date"]
    expiry = terms["warranty_expiry_date"]
    if terms["warranty_type"] == "No Warranty":
        return "No warranty", "", ""
    if not start and terms["warranty_period_days"]:
        start = str(posting_date)
    if not expiry and start and terms["warranty_period_days"]:
        expiry = str(add_days(start, terms["warranty_period_days"]))
    if not expiry:
        return "Expiry not recorded", start, ""
    if start and getdate(start) > as_of:
        return "Starts later", start, expiry
    return ("Active" if getdate(expiry) >= as_of else "Expired"), start, expiry


def _lines(sale, serial=None):
    _, meta = _child_meta(sale.doctype)
    rows = sale.get("items") or []
    bundles = voucher_serials(sale, rows)
    result = []
    as_of = getdate(today())
    for row in rows:
        serials = _serials(bundles.get(row.name) or row.get("serial_no"))
        if serial and serial not in serials:
            continue
        terms = _details(row, meta)
        if not terms["warranty_recorded"]:
            terms["warranty_period_days"] = row.get("custom_sos_warranty_days") or 0
            terms["warranty_expiry_date"] = str(row.get("custom_sos_warranty_expiry") or "")
        state, start, expiry = _coverage(terms, sale.posting_date, as_of)
        result.append({
            "row": row.name, "item_code": row.item_code, "item_name": row.item_name or row.item_code,
            "quantity": row.qty, "serials": serials, "status": state,
            "start": start, "expires": expiry, "days": terms["warranty_period_days"],
            "type": terms["warranty_type"], "terms": terms["warranty_terms"],
            "days_remaining": (getdate(expiry) - as_of).days if expiry else None,
        })
    return result


def _serial_record(serial, company):
    _require("Serial No")
    fields = ["name", "item_code", "item_name", "warranty_expiry_date", "warehouse", "status"]
    matches = frappe.get_list("Serial No", filters={"name": serial, "company": company},
                             fields=fields, limit_page_length=1)
    if not matches:
        frappe.throw("Serial number was not found for the active shop.")
    return matches[0]


def _serial_documents(serial, item_code, company):
    # Only call after checking the Serial No's permissions and shop. Voucher
    # details are returned via permission-checked parent queries below.
    docs = {doctype: [] for doctype in (*ALLOWED, "Purchase Receipt")}
    entries = frappe.get_all("Serial and Batch Entry", filters={
        "serial_no": serial, "parenttype": "Serial and Batch Bundle",
    }, pluck="parent")
    if entries:
        for bundle in frappe.get_all("Serial and Batch Bundle", filters={
            "name": ["in", list(set(entries))], "company": company, "item_code": item_code,
            "voucher_type": ["in", list(docs)],
        }, fields=["voucher_type", "voucher_no"]):
            if bundle.voucher_no:
                docs[bundle.voucher_type].append(bundle.voucher_no)
    for doctype in docs:
        if not frappe.has_permission(doctype, "read"):
            continue
        child = doctype + " Item"
        if frappe.get_meta(child).has_field("serial_no"):
            rows = frappe.get_all(child, filters={
                "parenttype": doctype, "docstatus": 1, "item_code": item_code,
                "serial_no": ["like", f"%{_term(serial)}%"],
            }, fields=["parent", "serial_no"])
            parents = [row.parent for row in rows if serial in _serials(row.serial_no)]
            docs[doctype].extend(parents)
    return docs


def _visible_documents(doctype, names, company, fields=None, page_size=12):
    if not names or not frappe.has_permission(doctype, "read"):
        return []
    return frappe.get_list(doctype, filters={
        "company": company, "docstatus": 1, "is_return": 0, "name": ["in", list(set(names))],
    }, fields=fields or ["name", "posting_date"], order_by="posting_date desc, creation desc",
        limit_page_length=page_size)


@frappe.whitelist(methods=["GET"])
def get_coverage(reference=None, kind="invoice"):
    company = _company()
    reference = _reference(reference, "invoice or serial number")
    serial = None
    receipts = []
    candidates = []
    if kind == "serial":
        serial = dict(_serial_record(reference, company))
        reference = serial["name"]
        docs = _serial_documents(reference, serial["item_code"], company)
        for doctype in ALLOWED:
            rows = _visible_documents(doctype, docs[doctype], company)
            candidates.extend((str(row.posting_date), doctype, row.name) for row in rows)
        receipts = _visible_documents("Purchase Receipt", docs["Purchase Receipt"], company,
                                      fields=["name", "supplier", "supplier_name", "posting_date"])
    elif kind == "invoice":
        for doctype in ALLOWED:
            rows = _visible_documents(doctype, [reference], company, page_size=1)
            candidates.extend((str(row.posting_date), doctype, row.name) for row in rows)
        if not candidates:
            frappe.throw("No submitted sales invoice with that number was found for the active shop.")
    else:
        frappe.throw("Choose an invoice or serial lookup.")

    invoices = []
    for _, doctype, name in sorted(candidates, reverse=True):
        sale = _sale(doctype, name, company)
        items = _lines(sale, serial=reference if serial else None)
        if items:
            invoices.append({
                "name": sale.name, "doctype": sale.doctype, "posting_date": sale.posting_date, "items": items,
                "customer": sale.get("customer_name") or sale.customer, "customer_id": sale.customer,
            })
    return {"invoices": invoices, "serial": serial, "receipts": receipts,
            "can_claim": bool(frappe.has_permission(CLAIM, "create"))}


@frappe.whitelist(methods=["GET"])
def find_customer_sales(invoice_type="Sales Invoice", search="", page=1):
    company = _company()
    if invoice_type not in ALLOWED:
        frappe.throw("Choose Sales Invoice or POS Invoice.")
    available = [doctype for doctype in ALLOWED if frappe.has_permission(doctype, "read")]
    if not available:
        frappe.throw("Sales Invoice or POS Invoice read permission is required.", frappe.PermissionError)
    if invoice_type not in available:
        invoice_type = available[0]
    term = _term(search)
    match = [[field, "like", f"%{term}%"] for field in ("name", "customer", "customer_name")] if term else None
    page = _page(page)
    rows = frappe.get_list(invoice_type, filters={"company": company, "docstatus": 1, "is_return": 0},
                           or_filters=match, fields=["name", "customer", "customer_name", "posting_date"],
                           order_by="posting_date desc, name desc", limit_start=(page - 1) * PAGE_SIZE,
                           limit_page_length=PAGE_SIZE + 1)
    return {"rows": rows[:PAGE_SIZE], "has_next": len(rows) > PAGE_SIZE,
            "available": available, "invoice_type": invoice_type}


@frappe.whitelist(methods=["GET"])
def list_claims(search="", status="", page=1):
    company = _company()
    _require(CLAIM)
    filters = {"company": company}
    if status:
        if status not in CLAIM_STATES:
            frappe.throw("Choose a valid claim status.")
        filters["status"] = status
    term = _term(search)
    meta = frappe.get_meta(CLAIM)
    extra = [field for field in CLAIM_FIELDS if meta.has_field(field)]
    search_fields = ["name", "serial_no", "customer_name", "item_code",
                     *(field for field in extra if field != "custom_sos_warranty_sale_type")]
    match = [[field, "like", f"%{term}%"] for field in search_fields] if term else None
    page = _page(page)
    rows = frappe.get_list(CLAIM, filters=filters, or_filters=match, fields=[
        "name", "status", "complaint_date", "customer", "customer_name", "serial_no", "item_code", "complaint", *extra,
    ], order_by="modified desc, name desc", limit_start=(page - 1) * PAGE_SIZE, limit_page_length=PAGE_SIZE + 1)
    return {"rows": rows[:PAGE_SIZE], "has_next": len(rows) > PAGE_SIZE}


@frappe.whitelist(methods=["POST"])
def create_claim(invoice=None, doctype=None, item_row=None, serial_no=None, complaint=None, issue_details=None):
    company = _company()
    _require(CLAIM, "create")
    serial_no = _reference(serial_no, "serial number")
    _serial_record(serial_no, company)
    complaint = _reference(complaint, "issue summary")
    details = str(issue_details or "").strip()
    if len(details) > 2000:
        frappe.throw("Issue details are limited to 2,000 characters.")
    sale = _sale(doctype, _reference(invoice, "invoice number"), company)
    line = next((row for row in _lines(sale, serial=serial_no) if row["row"] == item_row), None)
    if not line:
        frappe.throw("That serial number does not belong to the selected invoice line.")

    # Serialize duplicate checks for a physical device without committing
    # outside the successful Frappe POST transaction.
    frappe.db.get_value("Serial No", serial_no, "name", for_update=True)
    if frappe.db.get_value(CLAIM, {"company": company, "serial_no": serial_no,
                                "status": ["in", ["Open", "Work In Progress"]]},
                           "name", for_update=True):
        frappe.throw("An open claim already exists for this serial number. Check the Claims tab.")

    issue = f"Sale reference: {escape(sale.name)}"
    if details:
        issue += "<br>" + escape(details).replace("\n", "<br>")
    data = {
        "doctype": CLAIM, "company": company, "customer": sale.customer,
        "customer_name": sale.get("customer_name") or sale.customer,
        "serial_no": serial_no, "item_code": line["item_code"], "item_name": line["item_name"],
        "status": "Open", "complaint_date": today(), "complaint": complaint, "issue_details": issue,
    }
    if line["status"] in ("Active", "Expired", "No warranty"):
        data["warranty_amc_status"] = "Under Warranty" if line["status"] == "Active" else "Out of Warranty"
    if line["expires"]:
        data["warranty_expiry_date"] = line["expires"]
    if frappe.get_meta(CLAIM).has_field("custom_sos_warranty_sale"):
        data["custom_sos_warranty_sale_type"] = sale.doctype
        data["custom_sos_warranty_sale"] = sale.name
    doc = frappe.get_doc(data)
    doc.insert()
    return {"name": doc.name}


def _claim(name, action="read"):
    company = _company()
    _require(CLAIM, action)
    doc = frappe.get_doc(CLAIM, _reference(name, "claim number"))
    doc.check_permission("read")
    if action != "read":
        doc.check_permission(action)
    if doc.company != company:
        frappe.throw("Choose a warranty claim for the active shop.", frappe.PermissionError)
    return doc


@frappe.whitelist(methods=["GET"])
def get_claim(name):
    doc = _claim(name)
    return {
        "name": doc.name, "status": doc.status, "modified": str(doc.modified), "serial_no": doc.get("serial_no"),
        "customer": doc.get("customer_name") or doc.get("customer"),
        "item": doc.get("item_name") or doc.get("item_code"), "complaint": doc.get("complaint"),
        "issue_details": strip_html(doc.get("issue_details") or ""),
        "warranty_status": doc.get("warranty_amc_status"), "warranty_expiry": doc.get("warranty_expiry_date"),
        "opened": doc.get("complaint_date"), "resolved": doc.get("resolution_date"),
        "resolved_by": doc.get("resolved_by"), "resolution": strip_html(doc.get("resolution_details") or ""),
        "supplier_rma": doc.get("custom_sos_supplier_rma") or "",
        "invoice": doc.get("custom_sos_warranty_sale"),
        "invoice_type": doc.get("custom_sos_warranty_sale_type"),
        "can_edit": doc.docstatus == 0 and bool(doc.has_permission("write")),
    }


@frappe.whitelist(methods=["POST"])
def save_claim(name, modified, status, resolution="", supplier_rma=""):
    doc = _claim(name, "write")
    if doc.docstatus != 0 or str(doc.modified) != modified:
        frappe.throw("This claim changed or was locked. Reopen it and try again.")
    if status not in CLAIM_STATES:
        frappe.throw("Choose a valid claim status.")
    if doc.status in ("Closed", "Cancelled") and status != doc.status:
        frappe.throw("Open the claim in ERPNext to change its completed status.")
    resolution, supplier_rma = str(resolution or "").strip(), str(supplier_rma or "").strip()
    if len(resolution) > 2000 or len(supplier_rma) > 140:
        frappe.throw("Use up to 2,000 characters for the resolution and 140 for the supplier RMA.")
    if status in ("Closed", "Cancelled") and not resolution:
        frappe.throw("Enter the outcome before closing or cancelling a claim.")
    if supplier_rma or doc.get("custom_sos_supplier_rma"):
        if not frappe.get_meta(CLAIM).has_field("custom_sos_supplier_rma"):
            frappe.throw("Supplier RMA fields are missing. Run bench migrate for this site.")
        doc.set("custom_sos_supplier_rma", supplier_rma)
    if resolution != strip_html(doc.get("resolution_details") or "").strip():
        doc.resolution_details = escape(resolution).replace("\n", "<br>")
    if status == "Closed" and doc.status != "Closed":
        doc.resolution_date = now_datetime()
        doc.resolved_by = frappe.session.user
    doc.status = status
    doc.save()
    return {"name": doc.name, "status": doc.status}
