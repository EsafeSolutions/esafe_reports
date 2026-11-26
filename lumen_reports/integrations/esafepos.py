# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.

"""ESAFE POS entry points for the shared POS dashboard contract.

ESAFE POS resolves this module by dotted path at runtime. Keep the legacy
lumenpos entry points and the existing dashboard slug working through the same
implementation, including its permissions, entitlement checks and setup rules.
"""

import frappe

from lumen_reports.integrations import lumenpos


@frappe.whitelist(methods=["GET"])
def get_status():
	return lumenpos.get_status()


@frappe.whitelist(methods=["POST"])
def ensure_dashboard(lang: str | None = None):
	return lumenpos.ensure_dashboard(lang=lang)
