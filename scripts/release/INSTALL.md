# SERVICING OS release

This release includes the complete Git checkout and built Vue assets. If the ZIP includes `sample_invoice.html`, open it in your browser to see the demonstration invoice. The release combines the product picker, Service Job history and intake, stock receipt, Delivery Desk, invoice workspace, revenue streams, draft editing, and payment collection. Use this package for a fresh app install or to upgrade the existing app. Run the installer on the Bench host. A cashier using the same server on another PC can sign in through the browser.

## Upgrade the Mac Bench

Download the ZIP to Downloads and run:

```bash
cd /Users/mehediabdullah/ctf/servicing
unzip -o "$HOME/Downloads/RELEASE_NAME.zip" -d "$HOME/Downloads"
python3 "$HOME/Downloads/RELEASE_NAME/install_servicing_os.py" --site servicing.local
```

Restart the running development Bench and hard-refresh `/servicing-os`. The installer checks local source compatibility, backs up the site with files, rebuilds the Vue app when needed, migrates schema, prepares missing masters, verifies the result, and clears cache.

## Install or upgrade the Ubuntu Bench

Copy the ZIP to the Ubuntu host and run as the user who owns the Bench:

```bash
cd /home/rasel/frappe-bench-v15
unzip -o "$HOME/Downloads/RELEASE_NAME.zip" -d "$HOME/Downloads"
python3 "$HOME/Downloads/RELEASE_NAME/install_servicing_os.py" --site amcl.com --restart
```

Omit `--restart` on a development Bench and restart `bench start` manually. Add `--check` to run version and source preflight. With several companies, add `--company "NAME AS SHOWN IN ERPNEXT"`. If a company has multiple active shop records, set `servicing_os_shop` to the intended record in that site's configuration.

## Start from a new ERPNext site

The script requires an existing Frappe v15 Bench and Frappe/ERPNext v15 on the target site. Follow the official Frappe installation instructions for OS packages, then initialize v15 and create the target site. For example:

```bash
bench init --frappe-branch version-15 frappe-bench-v15
cd frappe-bench-v15
bench get-app erpnext https://github.com/frappe/erpnext --branch version-15
bench new-site shop.local
bench --site shop.local install-app erpnext
```

Start the Bench and complete the ERPNext Company setup wizard for the actual company and chart of accounts. Run the SERVICING OS installer with `--site shop.local`. It prepares the active Servicing Shop, warehouses, item groups, repair labor item, company-currency price lists, Cash ledger mapping, and the three revenue account mappings. Existing active configuration is reused. Configure real staff permissions and any additional bank payment modes for the company.

For an empty catalog, import or create Items with **Maintain Stock** enabled. The picker shows those Items even before stock arrives. To move the same shop and its customers, service history, stock, and invoices, use the original site backup and matching installed ERPNext apps, then run the installer against the restored site.

Official Bench commands: https://docs.frappe.io/framework/user/en/bench/bench-commands

## Open or print a saved invoice

From **Counter → Invoices → All invoices**, click an invoice number to open the saved checkout. The checkout shows the customer, item lines, totals and outstanding balance. Use **Edit Draft** or **Submit Draft Invoice** when permitted. Use **Receive payment** for a submitted sale with a balance due. The register's separate **Preview** action opens the print studio. The POS register can also open a saved checkout for review.

The Sales Invoice print studio uses a warm ivory layout with the amount in words next to the totals. The words follow the printed payable amount, including recorded rounding. It prints the invoice due date or its recorded instalment schedule. The footer includes saved item and device serials, configured company contact details, and an authorized signature line. The invoice barcode is at the bottom and the QR is at the bottom right.

The QR encodes the invoice number unless a verification link is configured. For a thermal print, choose the 80 mm paper size in your printer's settings and print at actual size. If a barcode cannot fit at a readable width, the printed invoice number and QR can still be used.


## Payments and handover

- In **Counter → Invoices → Sales invoices**, choose **Receive payment** on a submitted invoice with a positive balance. Enter the actual full or partial receipt, choose a mode, and record it. Bank modes require the transaction reference and date. The action is shown only while an invoice has a balance due.
- In **Service Jobs → Deliver Device**, review the invoice, check spare parts, and open **Receive payment**. For a draft, click **Submit invoice**. This finalizes approved parts and the invoice and opens the payment form if a balance is due and the cashier has permission. Confirm device handover after reviewing the new balance. Delivery on credit requires an explicit acknowledgment of the amount still due.
- For a delivered job, open **Delivery documents** to receive a remaining balance. The invoice register provides the same access.
- Payment uses ERPNext Payment Entry. The cashier needs Payment Entry create and submit permissions and an enabled company payment mode. Base-currency payments go through this screen. Foreign-currency and consolidated POS receipts use their ERPNext workflows.

## Keep the release in Git

On the existing Mac checkout, review the patched changes and commit them with the built public assets and updated page template:

```bash
cd /Users/mehediabdullah/ctf/servicing/apps/servicing_os
git status --short
git add -A -- README.md frontend servicing_os scripts/release
git diff --cached --stat
git commit -m "Upgrade SERVICING OS"
git push -u origin HEAD
```

Review the staged list for unrelated local files. The ZIP contains a standalone local Git repository for fresh installs. On a fresh installation you may configure its origin to your reviewed GitHub branch for future deployments.

Once the same release is merged into your deployment branch, remote hosts on that branch can pull it and provision the site:

```bash
cd /home/rasel/frappe-bench-v15
bench --site amcl.com backup --with-files
git -C apps/servicing_os pull --ff-only
bench --site amcl.com migrate
bench --site amcl.com execute servicing_os.site_setup.prepare
bench --site amcl.com execute servicing_os.deployment.verify
bench --site amcl.com clear-cache
bench restart
```

## Verification and rollback

Click an invoice number and confirm the saved checkout opens. Use **Preview** to verify A4, A5, 80 mm Thermal, and Delivery Note. Compare the printed total with its amount in words. Confirm the payment terms, footer serials and company contacts against ERPNext, then scan the two codes on a physical test print.

Open **Add Required Part** on an active job. Up to eight suggestions should appear as the field opens. Search by a single character or item code, add a part, and check its warehouse availability.

On a test site, open a submitted unpaid invoice, record a partial receipt, and compare the remaining amount with ERPNext. Then test delivery on a draft service invoice. Confirm the invoice is submitted before payment and the job moves to Delivered only after handover.

The installer prints its source backup path when it modifies an existing app. If the source check reports overlapping edits, the update pauses before applying them. Review those files together with the release patch using the actual installed source. To roll back the application, redeploy the previous app commit with its matching assets, or restore the original files listed in the installer backup and remove only the files marked as newly created. Clear cache and restart the old code. If a test site needs a full rollback, restore the corresponding Bench backup according to your site recovery process. Preserve live payments already collected and correct them through ERPNext's accounting workflow.

## Reuse and maintenance

The ZIP contains the full app as a local Git repository. From the extracted release folder, run:

```bash
git clone --branch release repository/servicing_os.git servicing_os-source
```

The app's `scripts/release/MAINTAIN.md` explains where to edit the reusable invoice document and how to build the next release. Keep previous released ZIPs to support upgrades from older versions.
