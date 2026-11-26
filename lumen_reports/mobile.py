# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary

"""Small runtime metadata for the installable POS dashboard.

Dashboard definitions and figures continue through the existing permission-checked
dashboard APIs. This endpoint never creates a dashboard or grants a role.
"""

import frappe

from lumen_reports.integrations import lumenpos


@frappe.whitelist(methods=["GET"])
def get_context():
	return {
		"connection": lumenpos.get_status(),
		"currency": frappe.db.get_single_value("Global Defaults", "default_currency") or "",
		"user": frappe.session.user,
	}
