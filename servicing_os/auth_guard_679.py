"""SERVICING OS 6.79 — read-only session and website routing helpers.

Never change authentication/session cookies. Let Frappe own credentials.
"""
import frappe

LOGIN_URL = '/login?redirect-to=%2Fservicing-os'


# Replaced by installer with the exact original hook dotted path, or None.
ORIGINAL_HOME_PAGE_HOOK = 'servicing_os.login_routes645.home_page'


def get_home_page(user):
    """Guest root => custom /login; authenticated users keep previous routing."""
    if user == 'Guest':
        return 'login'
    if ORIGINAL_HOME_PAGE_HOOK:
        # Preserve the existing app's routing logic instead of discarding it.
        return frappe.get_attr(ORIGINAL_HOME_PAGE_HOOK)(user) or 'servicing-os'
    return 'servicing-os'


def require_login():
    """Call before rendering the SERVICING OS website controller."""
    if not frappe.session or frappe.session.user == 'Guest':
        frappe.local.flags.redirect_location = LOGIN_URL
        raise frappe.Redirect


@frappe.whitelist(allow_guest=True, methods=['GET'])
def session_state():
    """Read-only, intentionally non-identifying check for the page session guard."""
    return {'logged_in': bool(frappe.session and frappe.session.user != 'Guest')}
