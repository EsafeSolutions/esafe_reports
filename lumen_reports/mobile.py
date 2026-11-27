# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary

"""Small runtime metadata for the installable POS dashboard.

Dashboard definitions and figures continue through the existing permission-checked
dashboard APIs. This endpoint never creates a dashboard or grants a role.
"""

import datetime

import frappe
from frappe import _

from lumen_reports import query_engine
from lumen_reports.integrations import lumenpos


@frappe.whitelist(methods=["GET"])
def get_context():
	return {
		"connection": lumenpos.get_status(),
		"currency": frappe.db.get_single_value("Global Defaults", "default_currency") or "",
		"user": frappe.session.user,
	}


@frappe.whitelist(methods=["GET"])
def get_returns(from_date: str, to_date: str, pos_profile: str | None = None, start=0):
	"""Return invoices for the mobile drill-down, with the viewer's permissions.

	The source, fields and submitted/return conditions are fixed here. Neither
	invoice lists nor totals use an unrestricted get_all or a client-supplied query.
	"""
	status = lumenpos.get_status()
	if not (status["can_view"] and status["can_read_source"] and not status["reason"]):
		frappe.throw(_("You do not have permission to view POS returns."), frappe.PermissionError)
	try:
		first = datetime.date.fromisoformat(from_date)
		last = datetime.date.fromisoformat(to_date)
		if first > last or first.isoformat() != from_date or last.isoformat() != to_date:
			raise ValueError
	except (TypeError, ValueError):
		frappe.throw(_("Choose a valid start and end date."))
	try:
		offset = int(start)
		if str(offset) != str(start) or offset < 0:
			raise ValueError
	except (TypeError, ValueError, OverflowError):
		frappe.throw(_("Invalid returns page."))
	if pos_profile is not None and (not isinstance(pos_profile, str) or len(pos_profile) > 140):
		frappe.throw(_("Choose a valid outlet."))
	filters = [["docstatus", "=", 1], ["is_return", "=", 1], ["posting_date", "between", [from_date, to_date]]]
	if pos_profile:
		filters.append(["pos_profile", "=", pos_profile])
	return query_engine.execute({
		"doctype": "POS Invoice",
		"fields": ["name", "posting_date", "customer", "grand_total", "currency", "return_against", "pos_profile"],
		"filters": filters,
		"sort": {"field": "creation", "order": "desc"},
		"limit": 20,
		"start": offset,
	})
