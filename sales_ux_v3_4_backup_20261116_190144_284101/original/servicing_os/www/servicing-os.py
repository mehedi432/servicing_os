import json
import os

import frappe


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = (
            "/login?redirect-to=/servicing-os"
        )
        raise frappe.Redirect

    context.no_cache = 1
    context.title = "SERVICING OS"

    manifest_path = frappe.get_app_path(
        "servicing_os",
        "public",
        "frontend",
        ".vite",
        "manifest.json",
    )

    if not os.path.exists(manifest_path):
        frappe.throw(
            "SERVICING OS frontend is not built. "
            "Run npx vite build."
        )

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    entry = manifest.get("index.html")

    if not entry:
        frappe.throw("Frontend entry missing from Vite manifest.")

    base_url = "/assets/servicing_os/frontend/"

    context.js_file = base_url + entry["file"]
    context.css_files = [
        base_url + css for css in entry.get("css", [])
    ]

    context.asset_tags = "\n".join(
        [
            *[
                '<link rel="stylesheet" href="{}">'.format(css)
                for css in context.css_files
            ],
            '<script type="module" src="{}"></script>'.format(
                context.js_file
            ),
        ]
    )
