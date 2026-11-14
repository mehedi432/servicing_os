"""Custom shop-facing login; administrators retain `/login?legacy=1`."""
import frappe


def resolve(path):
    # Preserve Frappe's native account recovery and SSO links when needed.
    if str(path or "").strip("/") == "login" and not frappe.form_dict.get("legacy"):
        return "servicing-login"
    return path


def home_page(user=None):
    """Direct shop operators to the shop app; Guest sees branded sign in."""
    if not user or user == 'Guest':
        return 'servicing-login'
    return 'servicing-os'
