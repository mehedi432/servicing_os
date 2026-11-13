import frappe
from frappe.utils import nowdate

COMPANY = "AL MODINA COMPUTERS LIMITED"
GROUP = "Computer Spare Parts"
WAREHOUSE = "Spare Parts - AMCL"
PRICE_LIST = "Standard Selling"

# Retailers' public advertised prices, looked up 2026-11-10.
# Reference/test selling prices only, NOT procurement cost, landed cost,
# current guaranteed quotations, or stock valuation.
PRODUCTS = [
    dict(code="AMCL-LEXAR-NM620-512", name="Lexar NM620 512GB M.2 NVMe SSD", rate=11700,
         source="Ryans", url="https://www.ryans.com/lexar-nm620-512gb-m.2-2280-pcie-gen-3-x-4-ssd"),
    dict(code="AMCL-LEXAR-NS100-256", name="Lexar NS100 256GB 2.5 inch SATA SSD", rate=6400,
         source="Ryans", url="https://www.ryans.com/category/internal-ssd-lexar"),
    dict(code="AMCL-LEXAR-NS100-512", name="Lexar NS100 512GB 2.5 inch SATA SSD", rate=10000,
         source="Ryans", url="https://www.ryans.com/category/internal-ssd-lexar"),
    dict(code="AMCL-NETAC-D8-3200", name="Netac Basic 8GB DDR4 3200MHz Desktop RAM", rate=8650,
         source="Ryans", url="https://www.ryans.com/netac-basic-8gb-ddr4-3200mhz-desktop-ram"),
    dict(code="AMCL-SMART-L8-3200", name="Smart 8GB DDR4 3200MHz Laptop SO-DIMM RAM", rate=7500,
         source="Ryans", url="https://www.ryans.com/smart-8gb-ddr4-3200mhz-laptop-ram"),
    dict(code="AMCL-ARCTIC-MX4-4G", name="Arctic MX-4 4g Thermal Paste", rate=1200,
         source="Star Tech", url="https://www.startech.com.bd/arctic-mx-4-4g-premium-performance-thermal-paste"),
    dict(code="AMCL-DEEPCOOL-Z5", name="Deepcool Z5 Thermal Paste", rate=650,
         source="Star Tech", url="https://www.startech.com.bd/deepcool-z5-thermal-paste"),
    dict(code="AMCL-UGREEN-US286-1M", name="UGREEN US286 1m USB-C to USB-C Cable", rate=349,
         source="Star Tech", url="https://www.startech.com.bd/ugreen-us286-usb-type-c-to-usb-type-c-1m-cable"),
]

def install():
    # Preflight: stop before any mutations if setup is not as expected.
    if not frappe.db.exists("Company", COMPANY):
        frappe.throw("Company not found: " + COMPANY)
    if not frappe.db.exists("Item Group", GROUP):
        frappe.throw("Item Group not found: " + GROUP)
    if frappe.db.get_value("Item Group", GROUP, "is_group"):
        frappe.throw("Item Group is a parent, expected a leaf: " + GROUP)
    if not frappe.db.exists("Warehouse", WAREHOUSE):
        frappe.throw("Warehouse missing: " + WAREHOUSE)
    wh = frappe.db.get_value("Warehouse", WAREHOUSE, ["company", "is_group", "disabled"], as_dict=True)
    if wh.company != COMPANY or wh.is_group or wh.disabled:
        frappe.throw("Invalid spare parts warehouse")
    if not frappe.db.exists("Price List", PRICE_LIST):
        frappe.throw("Standard Selling Price List is missing; set it up before proceeding")
    pl = frappe.db.get_value("Price List", PRICE_LIST, ["selling", "enabled", "currency"], as_dict=True)
    if not pl.selling or not pl.enabled:
        frappe.throw("Standard Selling must be an enabled selling price list")
    if pl.currency and pl.currency != "BDT":
        frappe.throw("Standard Selling price list uses unexpected currency: " + pl.currency)
    if not frappe.db.exists("UOM", "Nos"):
        frappe.throw("UOM Nos is missing")

    for p in PRODUCTS:
        if frappe.db.exists("Item", p["code"]):
            item = frappe.db.get_value("Item", p["code"],
                ["item_group", "is_stock_item", "is_sales_item", "stock_uom", "disabled"], as_dict=True)
            if (item.item_group != GROUP or not item.is_stock_item or
                    not item.is_sales_item or item.stock_uom != "Nos" or item.disabled):
                frappe.throw("Existing Item has conflicting setup; unchanged: " + p["code"])

    created_items, skipped_items, created_prices, skipped_prices = [], [], [], []
    for p in PRODUCTS:
        if frappe.db.exists("Item", p["code"]):
            skipped_items.append(p["code"])
        else:
            # These are proper stock Items but have ZERO stock until a real purchase/receipt.
            item = frappe.get_doc({
                "doctype": "Item", "item_code": p["code"],
                "item_name": p["name"], "item_group": GROUP,
                "stock_uom": "Nos", "is_stock_item": 1,
                "is_sales_item": 1, "is_purchase_item": 1,
                "disabled": 0,
                "description": ("Sample catalog item for repair and sales testing. "
                    "Retail reference on 2026-11-10: " + p["source"] + "; " + p["url"] +
                    ". Reference price is NOT purchase cost or current stock valuation."),
            })
            item.insert(ignore_permissions=True)
            created_items.append(p["code"])

        # Do not overwrite existing commercial prices. Only create a price if no
        # selling price in this price list exists for the item.
        existing_price = frappe.db.exists("Item Price", {
            "item_code": p["code"], "price_list": PRICE_LIST,
            "selling": 1,
        })
        if existing_price:
            skipped_prices.append(p["code"])
        else:
            doc = frappe.get_doc({
                "doctype": "Item Price", "item_code": p["code"],
                "price_list": PRICE_LIST, "selling": 1, "buying": 0,
                "price_list_rate": p["rate"], "currency": "BDT",
                "uom": "Nos", "valid_from": nowdate(),
            })
            doc.insert(ignore_permissions=True)
            created_prices.append({"item_code": p["code"], "bdt": p["rate"], "source": p["source"]})

    # bench execute handles commit on success and rollback on exception.
    return {
        "status": "success", "price_type": "retail reference / sample selling rate",
        "created_items": created_items, "already_existing_items": skipped_items,
        "created_item_prices": created_prices,
        "already_existing_item_prices_left_unchanged": skipped_prices,
        "opening_stock": 0, "stock_entries_created": 0,
        "invoices_created": 0, "payments_created": 0,
    }
