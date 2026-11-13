"""Read-only AMCL Service Job operational reports.

Periods select jobs by received_date. "Completed" and "Delivered" status
counts are CURRENT statuses, not historical completions during the period.
Optional milestone timestamps are drawn only from recorded repair-status
comments or the explicit actual_delivery field, never inferred from status.
"""
from datetime import date, timedelta
import html
import re

import frappe
from frappe.utils import nowdate

COMPANY = "AL MODINA COMPUTERS LIMITED"
ACCESS_ROLES = {"System Manager", "Accounts Manager"}
WORKLOG_PREFIX = "SERVICING_WORK_LOG_614D:"
VALID_REPORTS = {"register", "technicians", "aging"}


def _access():
    user = frappe.session.user
    if user != "Administrator" and not ACCESS_ROLES.intersection(set(frappe.get_roles(user))):
        frappe.throw("Owner or manager access is required for operational reports.", frappe.PermissionError)
    if not frappe.has_permission("Service Job", "read"):
        frappe.throw("Read permission is required for Service Job.", frappe.PermissionError)


def _dates(start_value=None, end_value=None):
    today = date.fromisoformat(nowdate())
    start_default = today.replace(day=1)
    try:
        start = date.fromisoformat(str(start_value)) if start_value else start_default
        end = date.fromisoformat(str(end_value)) if end_value else today
    except (TypeError, ValueError):
        frappe.throw("Dates must use YYYY-MM-DD format.")
    if start > end:
        frappe.throw("From Date cannot be later than To Date.")
    if (end - start).days > 365:
        frappe.throw("Please choose at most 366 calendar days.")
    return str(start), str(end), str(end + timedelta(days=1)), str(today)


def _filters(start, end_exclusive, technician, status, search, open_only=False):
    values = {"company": COMPANY, "start": start, "end_exclusive": end_exclusive}
    clauses = ["sj.received_date >= %(start)s", "sj.received_date < %(end_exclusive)s"]
    if frappe.get_meta("Service Job").has_field("shop"):
        clauses.append("sj.shop = %(company)s")
    if technician and technician != "All":
        if technician == "__unassigned__":
            clauses.append("(sj.technician IS NULL OR sj.technician = '')")
        else:
            if not frappe.db.exists("User", technician):
                frappe.throw("Unknown technician filter.")
            values["technician"] = technician
            clauses.append("sj.technician = %(technician)s")
    if status and status != "All":
        status_field = frappe.get_meta("Service Job").get_field("status")
        statuses = [x.strip() for x in (status_field.options or "").splitlines() if x.strip()] if status_field else []
        if status not in statuses:
            frappe.throw("Unknown Service Job status filter.")
        values["status"] = status
        clauses.append("sj.status = %(status)s")
    if search:
        search = str(search).strip()[:100]
        if search:
            values["pattern"] = "%" + search + "%"
            clauses.append("(sj.name LIKE %(pattern)s OR sj.customer_name LIKE %(pattern)s "
                           "OR sj.mobile LIKE %(pattern)s OR sj.brand LIKE %(pattern)s "
                           "OR sj.device_model LIKE %(pattern)s)")
    if open_only:
        clauses.append("sj.status NOT IN ('Delivered', 'Cancelled')")
    return " AND ".join(clauses), values


def _milestones(job_names):
    """Only status-change events actually recorded by the existing APIs."""
    if not job_names:
        return {}
    events = {}
    changes = frappe.db.sql("""
        SELECT reference_name, creation, content
          FROM `tabComment`
         WHERE reference_doctype = 'Service Job'
           AND comment_type = 'Comment'
           AND reference_name IN %(names)s
           AND content LIKE 'Repair status:%%'
         ORDER BY creation ASC
    """, {"names": tuple(job_names)}, as_dict=True)
    pattern = re.compile(r"^Repair status:.*?→\s*(Completed|Delivered)\s*\(by\b", re.I | re.S)
    for event in changes:
        text = html.unescape(str(event.content or "")).strip()
        match = pattern.search(text)
        if not match:
            continue
        field = "completed_recorded_at" if match.group(1).lower() == "completed" else "delivered_recorded_at"
        events.setdefault(event.reference_name, {}).setdefault(field, str(event.creation))
    return events


@frappe.whitelist(methods=["GET"])
def get_report_options():
    _access()
    status_field = frappe.get_meta("Service Job").get_field("status")
    statuses = [x.strip() for x in (status_field.options or "").splitlines() if x.strip()] if status_field else []
    shop_condition = " AND sj.shop = %(company)s" if frappe.get_meta("Service Job").has_field("shop") else ""
    technicians = frappe.db.sql("""
        SELECT DISTINCT sj.technician AS value,
               COALESCE(NULLIF(u.full_name, ''), sj.technician) AS label
          FROM `tabService Job` sj
          LEFT JOIN `tabUser` u ON u.name = sj.technician
         WHERE sj.technician IS NOT NULL AND sj.technician != ''
    """ + shop_condition + " ORDER BY label ASC LIMIT 200", {"company": COMPANY}, as_dict=True)
    return {"statuses": statuses, "technicians": technicians,
            "has_shop_filter": frappe.get_meta("Service Job").has_field("shop")}


@frappe.whitelist(methods=["GET"])
def get_operational_report(report="register", from_date=None, to_date=None,
                           technician=None, status=None, search=None, limit=300):
    """Read-only manager report. No INSERT, UPDATE, submit, or commit."""
    _access()
    report = str(report or "register").strip()
    if report not in VALID_REPORTS:
        frappe.throw("Unknown operational report.")
    start, end, end_exclusive, today = _dates(from_date, to_date)
    try:
        page_limit = max(1, min(int(limit), 500))
    except (ValueError, TypeError):
        frappe.throw("Invalid row limit.")
    search = str(search or "")
    where, params = _filters(start, end_exclusive, technician, status, search,
                              open_only=(report == "aging"))
    params.update({"as_of": today, "limit": page_limit})

    total_row = frappe.db.sql(
        "SELECT COUNT(*) AS n FROM `tabService Job` sj WHERE " + where,
        params, as_dict=True)
    total = int(total_row[0].n or 0)
    common = {
        "report": report, "company": COMPANY,
        "from_date": start, "to_date": end, "as_of": today,
        "received_date_filter": True, "total": total,
        "limit": page_limit, "truncated": total > page_limit,
        "note": "Dates filter when jobs were received; stage counts describe their current status."
    }

    if report == "register":
        meta = frappe.get_meta("Service Job")
        expected = "sj.expected_delivery" if meta.has_field("expected_delivery") else "NULL"
        actual = "sj.actual_delivery" if meta.has_field("actual_delivery") else "NULL"
        rows = frappe.db.sql("""
            SELECT sj.name, sj.received_date, sj.customer_name, sj.mobile,
                   sj.device_type, sj.brand, sj.device_model, sj.status, sj.priority,
                   sj.technician AS technician_id,
                   COALESCE(NULLIF(u.full_name, ''), sj.technician, 'Unassigned') AS technician,
                   """ + expected + """ AS expected_delivery,
                   """ + actual + """ AS actual_delivery
              FROM `tabService Job` sj
              LEFT JOIN `tabUser` u ON u.name = sj.technician
             WHERE """ + where + """
             ORDER BY sj.received_date DESC, sj.name DESC
             LIMIT %(limit)s
        """, params, as_dict=True)
        recorded = _milestones([row.name for row in rows])
        for row in rows:
            found = recorded.get(row.name, {})
            row["completed_recorded_at"] = found.get("completed_recorded_at")
            row["delivered_recorded_at"] = (
                found.get("delivered_recorded_at") or
                (str(row.actual_delivery) if row.actual_delivery else None))
        stage_rows = frappe.db.sql("""
            SELECT sj.status, COUNT(*) AS n
              FROM `tabService Job` sj WHERE """ + where + """
             GROUP BY sj.status
        """, params, as_dict=True)
        counts = {r.status: int(r.n) for r in stage_rows}
        common.update({"rows": rows,
                       "summary": {"jobs": total,
                                   "currently_completed": counts.get("Completed", 0),
                                   "currently_delivered": counts.get("Delivered", 0),
                                   "currently_waiting_parts": counts.get("Waiting for Parts", 0)},
                       "note": "Jobs received in the period. Completion/Delivery timestamps appear only when recorded; blank is unknown."})
        return common

    if report == "technicians":
        # Limited rows are technicians, not individual jobs. All matching jobs
        # enter the aggregate. Work notes count only current technician's own
        # time-stamped notes on matching jobs.
        rows = frappe.db.sql("""
            SELECT sj.technician AS technician_id,
                   COALESCE(NULLIF(u.full_name, ''), sj.technician, 'Unassigned') AS technician,
                   COUNT(*) AS total_jobs,
                   SUM(CASE WHEN sj.status NOT IN ('Delivered','Cancelled') THEN 1 ELSE 0 END) AS open_jobs,
                   SUM(CASE WHEN sj.status = 'Completed' THEN 1 ELSE 0 END) AS completed_now,
                   SUM(CASE WHEN sj.status = 'Ready to Deliver' THEN 1 ELSE 0 END) AS ready_now,
                   SUM(CASE WHEN sj.status = 'Delivered' THEN 1 ELSE 0 END) AS delivered_now,
                   SUM(CASE WHEN sj.status = 'Waiting for Parts' THEN 1 ELSE 0 END) AS waiting_parts,
                   SUM(CASE WHEN sj.status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled_now,
                   COALESCE(SUM(notes.note_count), 0) AS authored_notes,
                   ROUND(AVG(CASE WHEN sj.status NOT IN ('Delivered','Cancelled')
                       THEN GREATEST(DATEDIFF(%(as_of)s, DATE(sj.received_date)), 0)
                       ELSE NULL END), 1) AS avg_open_age_days
              FROM `tabService Job` sj
              LEFT JOIN `tabUser` u ON u.name = sj.technician
              LEFT JOIN (
                SELECT reference_name, owner, COUNT(*) AS note_count
                  FROM `tabComment`
                 WHERE reference_doctype = 'Service Job'
                   AND comment_type = 'Comment'
                   AND content LIKE 'SERVICING_WORK_LOG_614D:%%'
                 GROUP BY reference_name, owner
              ) notes ON notes.reference_name = sj.name AND notes.owner = sj.technician
             WHERE """ + where + """
             GROUP BY sj.technician, u.full_name
             ORDER BY open_jobs DESC, total_jobs DESC, technician ASC
             LIMIT %(limit)s
        """, params, as_dict=True)
        for r in rows:
            for key in ("total_jobs", "open_jobs", "completed_now", "ready_now",
                        "delivered_now", "waiting_parts", "cancelled_now", "authored_notes"):
                r[key] = int(r[key] or 0)
            r["avg_open_age_days"] = float(r.avg_open_age_days) if r.avg_open_age_days is not None else None
        # 'total' counts JOBS, not technician groups. Keep explicit row count.
        common.update({"rows": rows, "truncated": len(rows) >= page_limit and total > page_limit,
                       "summary": {"jobs": total, "technicians_shown": len(rows),
                                   "open_jobs": sum(r.open_jobs for r in rows)},
                       "note": "Jobs received in the period, grouped by CURRENT assignment and CURRENT status. 'Completed' and 'Delivered' are not historical period-event counts. Notes count only those written by the currently assigned technician."})
        return common

    buckets = frappe.db.sql("""
        SELECT COUNT(*) AS open_jobs,
               COALESCE(SUM(CASE WHEN DATEDIFF(%(as_of)s, DATE(sj.received_date)) <= 0 THEN 1 ELSE 0 END), 0) AS today,
               COALESCE(SUM(CASE WHEN DATEDIFF(%(as_of)s, DATE(sj.received_date)) BETWEEN 1 AND 2 THEN 1 ELSE 0 END), 0) AS days_1_2,
               COALESCE(SUM(CASE WHEN DATEDIFF(%(as_of)s, DATE(sj.received_date)) BETWEEN 3 AND 6 THEN 1 ELSE 0 END), 0) AS days_3_6,
               COALESCE(SUM(CASE WHEN DATEDIFF(%(as_of)s, DATE(sj.received_date)) BETWEEN 7 AND 14 THEN 1 ELSE 0 END), 0) AS days_7_14,
               COALESCE(SUM(CASE WHEN DATEDIFF(%(as_of)s, DATE(sj.received_date)) >= 15 THEN 1 ELSE 0 END), 0) AS days_15_plus
          FROM `tabService Job` sj WHERE """ + where,
        params, as_dict=True)[0]
    meta = frappe.get_meta("Service Job")
    expected = "sj.expected_delivery" if meta.has_field("expected_delivery") else "NULL"
    rows = frappe.db.sql("""
        SELECT sj.name, sj.received_date, sj.customer_name, sj.mobile,
               sj.status, sj.brand, sj.device_model, sj.priority,
               sj.technician AS technician_id,
               COALESCE(NULLIF(u.full_name, ''), sj.technician, 'Unassigned') AS technician,
               """ + expected + """ AS expected_delivery,
               GREATEST(DATEDIFF(%(as_of)s, DATE(sj.received_date)), 0) AS age_days
          FROM `tabService Job` sj
          LEFT JOIN `tabUser` u ON u.name = sj.technician
         WHERE """ + where + """
         ORDER BY age_days DESC, sj.received_date ASC, sj.name ASC
         LIMIT %(limit)s
    """, params, as_dict=True)
    for row in rows:
        days = int(row.age_days or 0)
        row["age_bucket"] = ("Today" if days == 0 else "1–2 days" if days <= 2 else
                             "3–6 days" if days <= 6 else "7–14 days" if days <= 14 else "15+ days")
        row["overdue_expected"] = bool(row.expected_delivery and str(row.expected_delivery)[:10] < today)
    common.update({"rows": rows,
                   "summary": {"open_jobs": int(buckets.open_jobs or 0),
                               "today": int(buckets.today or 0),
                               "days_1_2": int(buckets.days_1_2 or 0),
                               "days_3_6": int(buckets.days_3_6 or 0),
                               "days_7_14": int(buckets.days_7_14 or 0),
                               "days_15_plus": int(buckets.days_15_plus or 0)},
                   "note": "Open jobs as of today, received in the selected period. Delivered and Cancelled are excluded. Aging uses calendar days from received date."})
    return common
