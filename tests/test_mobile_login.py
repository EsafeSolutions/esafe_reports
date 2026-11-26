"""Installed-app entry points keep the normal Frappe sign-in flow."""

import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


class MobileLoginTests(unittest.TestCase):
    def test_mobile_launch_redirects_guest_to_login_and_returns_to_canonical_app(self):
        frappe = ModuleType("frappe")
        frappe.session = SimpleNamespace(user="Guest")
        frappe.local = SimpleNamespace(request=SimpleNamespace(path=""), flags=SimpleNamespace())
        frappe.Redirect = type("Redirect", (Exception,), {})
        package = ModuleType("lumen_reports")
        package.__path__ = [str(Path(__file__).resolve().parents[1] / "lumen_reports")]
        package.brand = SimpleNamespace()
        package.report = SimpleNamespace()
        with patch.dict(sys.modules, {"frappe": frappe, "lumen_reports": package}):
            page = importlib.import_module("lumen_reports.www.lumen")
            for path in ("/esafe-report/mobile", "/lumen/mobile/"):
                with self.subTest(path=path):
                    frappe.local.request.path = path
                    with self.assertRaises(frappe.Redirect):
                        page.get_context(SimpleNamespace())
                    self.assertEqual(frappe.local.flags.redirect_location, "/login?redirect-to=%2Fesafe-report%2Fmobile")
