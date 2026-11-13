import frappe


DOCTYPE = "Service Job"
MODULE = "Servicing OS"


def field(name, label, fieldtype="Data", **kwargs):
    return {
        "fieldname": name,
        "label": label,
        "fieldtype": fieldtype,
        **kwargs,
    }


def setup():
    if not frappe.conf.developer_mode:
        frappe.throw(
            "Enable developer_mode before creating standard DocTypes."
        )

    if not frappe.db.exists("Module Def", MODULE):
        frappe.throw("Module Servicing OS does not exist.")

    if frappe.db.exists("DocType", DOCTYPE):
        print("EXISTS: Service Job")
        return

    fields = [
        field(
            "shop", "Shop", "Link",
            options="Servicing Shop", reqd=1, in_list_view=1
        ),
        field(
            "received_date", "Received Date", "Datetime",
            reqd=1, default="Now", in_list_view=1
        ),
        field(
            "status", "Status", "Select",
            options="\n".join([
                "Received",
                "Diagnosing",
                "Waiting for Parts",
                "Repairing",
                "Ready to Deliver",
                "Delivered",
                "Cancelled",
            ]),
            default="Received",
            reqd=1,
            in_list_view=1,
        ),
        field(
            "priority", "Priority", "Select",
            options="Normal\nHigh\nUrgent",
            default="Normal",
            in_list_view=1,
        ),
        field(
            "customer_section", "Customer Details", "Section Break"
        ),
        field(
            "customer", "Customer", "Link",
            options="Customer", in_list_view=1
        ),
        field(
            "customer_name", "Customer Name",
            reqd=1, in_list_view=1
        ),
        field("mobile", "Mobile Number"),
        field(
            "device_section", "Device Details", "Section Break"
        ),
        field(
            "device_type", "Device Type", "Select",
            options="Laptop\nDesktop\nMonitor\nPrinter\nOther",
            reqd=1,
        ),
        field("brand", "Brand"),
        field("device_model", "Device Model"),
        field("serial_number", "Serial Number"),
        field(
            "repair_section", "Repair Details", "Section Break"
        ),
        field(
            "reported_problem", "Reported Problem", "Small Text",
            reqd=1,
        ),
        field(
            "accessories_received",
            "Accessories Received", "Small Text"
        ),
        field("diagnosis", "Diagnosis", "Small Text"),
        field(
            "technician", "Assigned Technician", "Link",
            options="User"
        ),
        field(
            "financial_section", "Financial Details", "Section Break"
        ),
        field(
            "estimated_cost", "Estimated Cost", "Currency",
            default="0"
        ),
        field(
            "final_repair_cost", "Final Repair Cost", "Currency",
            default="0"
        ),
        field(
            "delivery_section", "Delivery Details", "Section Break"
        ),
        field(
            "expected_delivery", "Expected Delivery", "Datetime"
        ),
        field(
            "actual_delivery", "Actual Delivery", "Datetime"
        ),
        field("remarks", "Remarks", "Small Text"),
    ]

    doc = frappe.get_doc({
        "doctype": "DocType",
        "name": DOCTYPE,
        "module": MODULE,
        "custom": 0,
        "istable": 0,
        "issingle": 0,
        "is_submittable": 0,
        "autoname": "SRV-.YYYY.-.#####",
        "title_field": "customer_name",
        "search_fields": "customer_name,mobile,serial_number",
        "track_changes": 1,
        "fields": fields,
        "permissions": [
            {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1,
                "report": 1,
                "export": 1,
                "print": 1,
            }
        ],
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    print("CREATED: Service Job")
    print("NUMBERING: SRV-YYYY-00001")
    print("FIELDS:", len(fields))


if __name__ == "__main__":
    setup()
