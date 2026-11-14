"""Ivory shop login; ERPNext remains the identity and permissions backend."""
import frappe

no_cache = True


def get_context(context):
    context.no_cache = True
    context.no_header = True
    context.no_footer = True
    context.show_sidebar = False
    context.title = "SERVICING OS | Sign in"
    if frappe.session.user != "Guest" and not frappe.form_dict.get("preview"):
        frappe.local.flags.redirect_location = "/servicing-os"
        raise frappe.Redirect
