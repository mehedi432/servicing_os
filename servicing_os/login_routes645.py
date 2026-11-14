"""Frappe website routing for SERVICING OS; no desk/auth monkey-patching."""
import frappe


def home_page(user=None):
    return "servicing-login" if not user or user == "Guest" else "servicing-os"


def resolve(path):
    """Use the ivory page for /login, retaining ?legacy=1 for native recovery."""
    if str(path or "").strip("/") == "login" and not frappe.form_dict.get("legacy"):
        return "servicing-login"
    return path
