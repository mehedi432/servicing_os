"""Read-only inventory hero top-selling products for SERVICING OS / ERPNext v15.

Submitted Sales Invoices only; returns subtract stock-unit quantities. A chosen
warehouse constrains the sale-line warehouse. Never changes inventory data.
"""

import frappe
from frappe.utils import add_days, flt, today

from servicing_os.api.inventory_workspace import _company, _warehouses


@frappe.whitelist(methods=["GET"])
def get_hero_sellers(warehouse=None, days=90):
    if frappe.session.user == "Guest":
        frappe.throw("Login is required", frappe.PermissionError)
    company = _company()  # Active shop and shop permissions handled centrally.
    if not frappe.has_permission("Item", "read") or not frappe.has_permission("Bin", "read"):
        frappe.throw("Item and Bin read permissions are required", frappe.PermissionError)
    permitted = {w.name for w in _warehouses(company)}
    warehouse = str(warehouse or "").strip()
    if warehouse and warehouse not in permitted:
        frappe.throw("Warehouse is unavailable for this shop", frappe.PermissionError)
    try:
        days = int(days)
    except (TypeError, ValueError):
        frappe.throw("Days must be a number")
    if days < 7 or days > 365:
        frappe.throw("Days must be between 7 and 365")
    begin = add_days(today(), -(days - 1))
    end = today()
    answer = {
        "status": "no_submitted_sales",
        "period_days": days,
        "warehouse": warehouse,
        "partial": False,
        "top": [],
        "total_units": 0.0,
        "source": "submitted_sales_invoices",
    }
    admin = frappe.session.user == "Administrator"
    if not admin and not frappe.has_permission("Sales Invoice", "read"):
        answer["status"] = "permission_denied"
        return answer

    filters = {"company": company, "docstatus": 1, "posting_date": ["between", [begin, end]]}

    if admin:
        # Restricted to the single active shop company. Only the built-in
        # Administrator can use this complete set-level aggregation; for other
        # users permission-aware invoice reads are mandatory.
        condition = " AND sii.warehouse = %s" if warehouse else ""
        params = [company, begin, end] + ([warehouse] if warehouse else [])
        sql = """
            SELECT sii.item_code, MAX(it.item_name) AS item_name,
              SUM(CASE WHEN COALESCE(si.is_return, 0) = 1
                THEN -ABS(COALESCE(sii.stock_qty, 0))
                ELSE COALESCE(sii.stock_qty, 0) END) AS sold_units
            FROM `tabSales Invoice` si
            INNER JOIN `tabSales Invoice Item` sii
                ON sii.parent = si.name AND sii.parenttype = 'Sales Invoice'
            INNER JOIN `tabItem` it ON it.name = sii.item_code
            WHERE si.company = %s AND si.docstatus = 1
              AND si.posting_date BETWEEN %s AND %s
              AND it.disabled = 0 AND it.is_stock_item = 1
        """ + condition + """
            GROUP BY sii.item_code
            HAVING sold_units > 0
            ORDER BY sold_units DESC, sii.item_code ASC
            LIMIT 5001
        """
        rows = frappe.db.sql(sql, tuple(params), as_dict=True)
        if not rows:
            answer["status"] = ("no_stock_sales" if frappe.db.exists("Sales Invoice", filters)
                                else "no_submitted_sales")
            return answer
        if len(rows) > 5000:
            answer["partial"] = True
        rows = rows[:5000]
        counts = [(r.item_code, r.item_name or r.item_code, max(0.0, flt(r.sold_units))) for r in rows]
    else:
        # Invoice permissions + company filter before child rows. The cap avoids
        # unbounded data extraction and always marks incomplete rankings.
        invoices = frappe.get_list("Sales Invoice", filters=filters,
            fields=["name", "is_return"], order_by="posting_date desc, name desc",
            limit_page_length=4001)
        if not invoices:
            return answer
        if len(invoices) > 4000:
            answer["partial"] = True
        invoices = invoices[:4000]
        returns = {r.name: bool(r.is_return) for r in invoices}
        item_list = frappe.get_list("Item", filters={"disabled": 0, "is_stock_item": 1},
            fields=["name", "item_name"], limit_page_length=2501)
        if len(item_list) > 2500:
            answer["partial"] = True
        item_names = {r.name: r.item_name or r.name for r in item_list[:2500]}
        totals = {}
        ids = list(returns)
        for p in range(0, len(ids), 150):
            children = frappe.get_all("Sales Invoice Item",
                filters={"parenttype": "Sales Invoice", "parent": ["in", ids[p:p+150]]},
                fields=["parent", "item_code", "stock_qty", "warehouse"],
                limit_page_length=20001)
            if len(children) > 20000:
                answer["partial"] = True
            for row in children[:20000]:
                if row.item_code not in item_names:
                    continue
                if warehouse and row.warehouse != warehouse:
                    continue
                qty = flt(row.stock_qty)
                if returns.get(row.parent):
                    qty = -abs(qty)
                totals[row.item_code] = totals.get(row.item_code, 0.0) + qty
        counts = [(code, item_names[code], qty) for code, qty in totals.items() if qty > 0]
        counts.sort(key=lambda r: (-r[2], r[0]))

    if not counts:
        answer["status"] = "no_stock_sales"
        return answer
    answer["status"] = "ready"
    answer["total_units"] = round(sum(qty for _, _, qty in counts), 3)
    answer["top"] = [{"item_code": code, "item_name": name, "sold_units": round(qty, 3)}
                     for code, name, qty in counts[:5]]
    return answer
