"""Public SERVICING OS sign-in page; authenticates using native Frappe login."""
import frappe
no_cache = True
def get_context(context):
    context.no_cache = True
    context.title = 'Sign in · SERVICING OS'
    context.no_header = True
    context.no_footer = True
