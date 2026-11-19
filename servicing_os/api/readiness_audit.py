
import frappe
import json


def run():
    """Read-only inventory and accounting configuration audit."""

    def fields_of(doctype):
        return {
            f.fieldname
            for f in frappe.get_meta(doctype).fields
        } | {"name"}

    def safe_fields(doctype, wanted):
        available = fields_of(doctype)
        return [f for f in wanted if f in available]

    def rows(doctype, wanted, filters=None, limit=30):
        return frappe.get_all(
            doctype,
            fields=safe_fields(doctype, wanted),
            filters=filters or {},
            limit_page_length=limit,
            order_by="name asc",
        )

    def count(doctype, filters=None):
        return frappe.db.count(
            doctype,
            filters=filters or {},
        )

    report = {
        "site": frappe.local.site,
        "audit_type": "READ ONLY",
        "companies": [],
        "warehouses": [],
        "items": {},
        "accounts": {},
        "payments": {},
        "settings": {},
        "transactions": {},
        "warnings": [],
    }

    report["companies"] = rows(
        "Company",
        [
            "name",
            "abbr",
            "default_currency",
            "country",
            "default_receivable_account",
            "default_payable_account",
            "default_income_account",
            "default_expense_account",
            "cost_center",
        ],
    )

    report["warehouses"] = rows(
        "Warehouse",
        [
            "name",
            "company",
            "is_group",
            "disabled",
            "warehouse_type",
        ],
    )

    report["items"] = {
        "total": count("Item"),
        "stock_items": count(
            "Item", {"is_stock_item": 1}
        ),
        "non_stock_items": count(
            "Item", {"is_stock_item": 0}
        ),
        "disabled": count(
            "Item", {"disabled": 1}
        ),
        "sample_stock_items": rows(
            "Item",
            [
                "name",
                "item_name",
                "item_group",
                "stock_uom",
                "is_stock_item",
                "disabled",
            ],
            {"is_stock_item": 1},
            10,
        ),
        "sample_service_items": rows(
            "Item",
            [
                "name",
                "item_name",
                "item_group",
                "stock_uom",
                "is_stock_item",
                "disabled",
            ],
            {"is_stock_item": 0},
            10,
        ),
    }

    report["accounts"] = {
        "receivable": rows(
            "Account",
            [
                "name",
                "company",
                "account_type",
                "root_type",
                "is_group",
            ],
            {
                "account_type": "Receivable",
                "is_group": 0,
            },
        ),
        "income": rows(
            "Account",
            [
                "name",
                "company",
                "account_type",
                "root_type",
                "is_group",
            ],
            {
                "root_type": "Income",
                "is_group": 0,
            },
        ),
        "cash": rows(
            "Account",
            [
                "name",
                "company",
                "account_type",
                "root_type",
                "is_group",
            ],
            {
                "account_type": "Cash",
                "is_group": 0,
            },
        ),
        "bank": rows(
            "Account",
            [
                "name",
                "company",
                "account_type",
                "root_type",
                "is_group",
            ],
            {
                "account_type": "Bank",
                "is_group": 0,
            },
        ),
    }

    report["payments"] = {
        "modes": rows(
            "Mode of Payment",
            ["name", "type", "enabled"],
        ),
        "existing_payment_entries": count(
            "Payment Entry"
        ),
    }

    stock_fields = safe_fields(
        "Stock Settings",
        [
            "valuation_method",
            "allow_negative_stock",
            "default_warehouse",
            "auto_insert_price_list_rate_if_missing",
        ],
    )

    for field in stock_fields:
        if field != "name":
            report["settings"][field] = (
                frappe.db.get_single_value(
                    "Stock Settings", field
                )
            )

    report["transactions"] = {
        "service_jobs": count("Service Job"),
        "sales_invoices": count("Sales Invoice"),
        "purchase_invoices": count("Purchase Invoice"),
        "stock_entries": count("Stock Entry"),
        "delivery_notes": count("Delivery Note"),
        "payment_entries": count("Payment Entry"),
    }

    if not report["companies"]:
        report["warnings"].append(
            "No Company configured."
        )

    usable_warehouses = [
        w for w in report["warehouses"]
        if not w.get("is_group")
        and not w.get("disabled")
    ]

    if not usable_warehouses:
        report["warnings"].append(
            "No active non-group Warehouse found."
        )

    if not report["accounts"]["receivable"]:
        report["warnings"].append(
            "No receivable ledger found."
        )

    if not report["accounts"]["income"]:
        report["warnings"].append(
            "No income ledger found."
        )

    if not report["accounts"]["cash"] \
       and not report["accounts"]["bank"]:
        report["warnings"].append(
            "No Cash or Bank account found."
        )

    if report["settings"].get("allow_negative_stock"):
        report["warnings"].append(
            "Negative stock is allowed; review "
            "before repair parts issuing."
        )

    print(json.dumps(
        report,
        indent=2,
        default=str,
    ))

    return report
