# Maintain invoices and releases

Keep the app source in Git. Invoices, settings, and schema migrations are managed by the existing Frappe and ERPNext sites.

| For changes to | Edit |
| :--- | :--- |
| Invoice layout, footer, serial placement, and payment terms | `frontend/src/components/InvoiceDocument.vue` |
| Print typography and paper-specific spacing | `frontend/src/components/invoice-paper.css` |
| Page options, barcode, QR, and print markup | `frontend/src/components/invoice-print.mjs` |
| Preview dialog and format controls | `frontend/src/components/SalesInvoiceStudio.vue` |
| Payable amount in words, recorded rounding, serials, and payment schedules | `servicing_os/invoice_printing.py` |

Update the saved company and Servicing Shop contact details for branding changes. Use `InvoiceDocument.vue` from a new screen by passing the saved receipt, invoice name, optional paper format, and copy type. The page and the print window share one invoice layout and stylesheet. Keep invoice data on the existing permission-checked endpoints. The Delivery Note uses the same document with financial fields hidden.

## Build and check the changes

Run from the app checkout:

```bash
npm --prefix frontend ci
npm --prefix frontend run test:invoice
npm --prefix frontend run build
python3 -m unittest discover -s scripts/release/tests
git diff --check
```

Open Sales Invoices and compare Print Preview for A4, A5, 80 mm thermal, and Delivery Note. Verify the payable amount in words, dates, printed serials, and physical scans using a test invoice. Verify Frappe and ERPNext v15 on a staging site before updating production.

## Build the next ZIP

Use Python 3.12 or later and Git on the release machine. Build and commit the Vue bundles alongside the source changes. Run the builder with the deployed Git baseline and the release commit or tag. Pass earlier ZIPs as `--previous` when the installer needs to recognize their original source. Optional flags can be repeated for multiple supported releases.

```bash
python3 scripts/release/build_release.py \
  --base YOUR_DEPLOYED_GIT_TAG \
  --ref YOUR_NEW_RELEASE_GIT_TAG \
  --previous /path/to/previous-release.zip \
  --output /path/to/servicing_os_release.zip
```

For a release candidate, stage your changes including generated frontend assets and use `--staged` in place of `--ref`. For a single Git baseline, omit `--previous`. To include a demo, add `--sample /path/to/sample_invoice.html`.

The builder validates the Frappe template and its frontend asset references, writes the installable source, and checks the ZIP. Its template and installer live in this directory. Use the Git patch when a release intentionally deletes source files. The overlay installer preserves existing files that are absent from the new source tree.

## Install the ZIP

Follow `README.md` inside the ZIP for preflight, backups, Mac or Ubuntu installation, migration, and rollback. The installer supports fresh and existing benches. To inspect the full source without running Bench, clone `repository/servicing_os.git` from the extracted ZIP.
