app_name = "servicing_os"
app_title = "Servicing Os"
app_publisher = "Abdullah Al Mehedi"
app_description = "A open source tool for servicing shops in Bangladesh."
app_email = "aamehedi15@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "servicing_os",
# 		"logo": "/assets/servicing_os/logo.png",
# 		"title": "Servicing Os",
# 		"route": "/servicing_os",
# 		"has_permission": "servicing_os.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/servicing_os/css/servicing_os.css"
# app_include_js = "/assets/servicing_os/js/servicing_os.js"

# include js, css files in header of web template
# web_include_css = "/assets/servicing_os/css/servicing_os.css"
# web_include_js = "/assets/servicing_os/js/servicing_os.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "servicing_os/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "servicing_os/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "servicing_os.utils.jinja_methods",
# 	"filters": "servicing_os.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "servicing_os.install.before_install"
# after_install = "servicing_os.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "servicing_os.uninstall.before_uninstall"
# after_uninstall = "servicing_os.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "servicing_os.utils.before_app_install"
# after_app_install = "servicing_os.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "servicing_os.utils.before_app_uninstall"
# after_app_uninstall = "servicing_os.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "servicing_os.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "servicing_os.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "servicing_os.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["servicing_os.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"servicing_os.tasks.all"
# 	],
# 	"daily": [
# 		"servicing_os.tasks.daily"
# 	],
# 	"hourly": [
# 		"servicing_os.tasks.hourly"
# 	],
# 	"weekly": [
# 		"servicing_os.tasks.weekly"
# 	],
# 	"monthly": [
# 		"servicing_os.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "servicing_os.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "servicing_os.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "servicing_os.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["servicing_os.utils.before_request"]
# after_request = ["servicing_os.utils.after_request"]

# Job Events
# ----------
# before_job = ["servicing_os.utils.before_job"]
# after_job = ["servicing_os.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"servicing_os.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# S645_SERVICING_AUTH_IVORY
homepage = 'servicing-login'
# SERVICING_OS_AUTH_GUARD_679: Guest => login; authenticated users delegate to original servicing_os.login_routes645.home_page
get_website_user_home_page = "servicing_os.auth_guard_679.get_home_page"
website_path_resolver = 'servicing_os.login_routes645.resolve'

# SERVICING_OS_COUNTER_657 — automated customer delivery status AFTER native invoice submission.
# Retain existing doc_events handlers; append rather than overwrite them.
_sos657_events = {
    'on_submit': 'servicing_os.api.invoice_delivery_657.on_invoice_submit',
    'on_cancel': 'servicing_os.api.invoice_delivery_657.on_invoice_cancel',
}
try:
    doc_events
except NameError:
    doc_events = {}
for _sos657_dt in ('Sales Invoice', 'POS Invoice'):
    _sos657_dt_events = doc_events.setdefault(_sos657_dt,{})
    for _sos657_ev, _sos657_handler in _sos657_events.items():
        _sos657_prior = _sos657_dt_events.get(_sos657_ev)
        if not _sos657_prior:
            _sos657_dt_events[_sos657_ev] = _sos657_handler
        elif isinstance(_sos657_prior, str):
            _sos657_dt_events[_sos657_ev] = [_sos657_prior,_sos657_handler]
        elif isinstance(_sos657_prior, (list, tuple)):
            _sos657_dt_events[_sos657_ev] = list(_sos657_prior) + [_sos657_handler]
        else:
            raise TypeError('Unsupported existing doc_events entry in SERVICING OS hooks.py')
del _sos657_events, _sos657_dt, _sos657_dt_events, _sos657_ev, _sos657_handler, _sos657_prior

# SERVICING_OS_COUNTER_657


# SERVICING_OS_671: merge with any existing invoice hooks; do not replace them.
_sos671_doc_events = globals().get('doc_events')
if _sos671_doc_events is None:
    _sos671_doc_events = {}
    doc_events = _sos671_doc_events
if not isinstance(_sos671_doc_events, dict):
    raise TypeError('SERVICING OS 6.71 expects doc_events to be a dict')
for _sos671_dt in ('Sales Invoice', 'POS Invoice'):
    _sos671_actions = _sos671_doc_events.setdefault(_sos671_dt, {})
    if not isinstance(_sos671_actions, dict):
        raise TypeError('doc_events entry is not a dict: ' + _sos671_dt)
    _sos671_current = _sos671_actions.get('before_submit')
    _sos671_target = 'servicing_os.api.item_warranty_671.populate_invoice_warranty'
    if _sos671_current is None:
        _sos671_actions['before_submit'] = _sos671_target
    elif isinstance(_sos671_current, str):
        if _sos671_current != _sos671_target:
            _sos671_actions['before_submit'] = [_sos671_current, _sos671_target]
    elif isinstance(_sos671_current, (list, tuple)):
        if _sos671_target not in _sos671_current:
            _sos671_actions['before_submit'] = list(_sos671_current) + [_sos671_target]
    else:
        raise TypeError('Unsupported before_submit hook type: '+_sos671_dt)
del _sos671_doc_events, _sos671_dt, _sos671_actions, _sos671_current, _sos671_target
