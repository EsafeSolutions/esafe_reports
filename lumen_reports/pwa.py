# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary

"""Public service-worker script; no session data or credentials are included."""

from pathlib import Path

import frappe
from werkzeug.wrappers import Response


@frappe.whitelist(allow_guest=True, methods=["GET"])
def service_worker():
	root = Path(frappe.get_app_path("lumen_reports", "public"))
	version_file = root / "frontend" / "version.json"
	version = frappe.parse_json(version_file.read_text(encoding="utf-8")).get("version", "1") if version_file.exists() else "1"
	script = (root / "pwa" / "sw.js").read_text(encoding="utf-8").replace("__LUMEN_BUILD__", str(version))
	return Response(script, mimetype="application/javascript", headers={
		"Service-Worker-Allowed": "/esafe-report/",
		"Cache-Control": "no-cache, no-store, must-revalidate",
		"X-Content-Type-Options": "nosniff",
	})
