
import re
import frappe


def normalize_mobile(value):
    digits = re.sub(r"\D", "", str(value or ""))

    if len(digits) == 13 and digits.startswith("8801"):
        return "0" + digits[3:]

    if len(digits) == 11 and digits.startswith("01"):
        return digits

    if len(digits) == 10 and digits.startswith("1"):
        return "0" + digits

    return digits


def valid_mobile(value):
    return bool(
        re.fullmatch(r"01[3-9][0-9]{8}", normalize_mobile(value))
    )


def mobile_variants(value):
    mobile = normalize_mobile(value)

    if not valid_mobile(mobile):
        return []

    return [
        mobile,
        "88" + mobile,
        "+88" + mobile,
        mobile[1:],
    ]


def find_by_mobile(value):
    mobile = normalize_mobile(value)

    if not valid_mobile(mobile):
        return None

    # First use the exact-match query.
    rows = frappe.get_list(
        "Customer",
        filters={"mobile_no": ["in", mobile_variants(mobile)]},
        fields=["name", "customer_name", "mobile_no"],
        limit_page_length=20,
    )

    # Also support older numbers with spaces, hyphens or brackets.
    # This bounded suffix search is a compatibility fallback.
    suffix = mobile[-8:]

    legacy = frappe.get_list(
        "Customer",
        filters={"mobile_no": ["like", "%" + suffix + "%"]},
        fields=["name", "customer_name", "mobile_no"],
        limit_page_length=100,
    )

    seen = set()
    matches = []

    for row in rows + legacy:
        if row.name in seen:
            continue
        seen.add(row.name)

        if normalize_mobile(row.mobile_no) == mobile:
            matches.append(row)

    if len(matches) > 1:
        frappe.throw(
            "Multiple Customers have the same mobile number. "
            "Please resolve these duplicate Customer records."
        )

    return matches[0] if matches else None


@frappe.whitelist(methods=["GET"])
def search_customers(q=""):
    if frappe.session.user == "Guest":
        frappe.throw("Login required", frappe.PermissionError)

    if not frappe.has_permission("Customer", "read"):
        frappe.throw(
            "Customer read permission required",
            frappe.PermissionError,
        )

    q = str(q or "").strip()[:80]

    if len(q) < 2:
        return []

    fields = ["name", "customer_name", "mobile_no"]
    digits = re.sub(r"\D", "", q)

    if len(digits) >= 3:
        mobile = normalize_mobile(q)

        if valid_mobile(mobile):
            exact = find_by_mobile(mobile)
            if exact:
                return [exact]

        # Search the mobile field, not the customer name.
        # Search remains bounded to eight suggestions.
        variants = [digits]

        if digits.startswith("880"):
            variants.append("0" + digits[3:])
        elif digits.startswith("01"):
            variants.append("88" + digits)

        results = []
        seen = set()

        for part in variants:
            rows = frappe.get_list(
                "Customer",
                filters={
                    "mobile_no": ["like", "%" + part + "%"]
                },
                fields=fields,
                limit_page_length=8,
            )

            for row in rows:
                if row.name not in seen:
                    seen.add(row.name)
                    results.append(row)

                if len(results) >= 8:
                    return results

        return results

    return frappe.get_list(
        "Customer",
        filters={
            "customer_name": ["like", "%" + q + "%"]
        },
        fields=fields,
        order_by="customer_name asc",
        limit_page_length=8,
    )


def resolve_customer(name, mobile, selected_customer=None):
    if not frappe.has_permission("Customer", "read"):
        frappe.throw(
            "Customer read permission required",
            frappe.PermissionError,
        )

    mobile = normalize_mobile(mobile)

    if not valid_mobile(mobile):
        frappe.throw(
            "Enter a valid Bangladesh mobile number"
        )

    # Serialize customer creation for the same mobile number.
    # This lock is connection-scoped and released in finally.
    lock_name = "servicing_customer_" + mobile
    acquired = frappe.db.sql(
        "SELECT GET_LOCK(%s, 10)", (lock_name,)
    )[0][0]

    if acquired != 1:
        frappe.throw(
            "Customer record is busy. Please try again."
        )

    try:
        existing = find_by_mobile(mobile)

        if selected_customer:
            selected_customer = str(selected_customer).strip()

            if not frappe.has_permission(
                "Customer", "read", doc=selected_customer
            ):
                frappe.throw("Cannot access selected Customer")

            selected = frappe.get_doc(
                "Customer", selected_customer
            )

            if normalize_mobile(selected.mobile_no) != mobile:
                frappe.throw(
                    "Selected Customer mobile does not match. "
                    "Please select the correct Customer."
                )

            if existing and existing.name != selected.name:
                frappe.throw(
                    "Another Customer uses this mobile number"
                )

            return selected.name, False

        if existing:
            return existing.name, False

        if not frappe.has_permission("Customer", "create"):
            frappe.throw(
                "Customer create permission required",
                frappe.PermissionError,
            )

        doc = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": str(name or "").strip(),
            "customer_type": "Individual",
            "customer_group": "Individual",
            "territory": "Bangladesh",
            "mobile_no": mobile,
        })

        doc.insert()

        return doc.name, True

    finally:
        frappe.db.sql(
            "SELECT RELEASE_LOCK(%s)", (lock_name,)
        )
