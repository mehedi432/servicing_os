import frappe

@frappe.whitelist(methods=["GET"])
def recent_customers():
    """Eight most recently modified customers visible to the current user."""
    customers = frappe.get_list(
        "Customer",
        fields=["name", "customer_name", "mobile_no"],
        order_by="modified desc",
        limit_page_length=8,
    )
    return {"results": customers}
