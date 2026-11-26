"""Contract guard tests with a fake Frappe runtime; no database/site is modified."""

import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class POSContractTests(unittest.TestCase):
    def setUp(self):
        self.frappe = ModuleType("frappe")
        self.frappe._ = lambda text: text
        self.allowed_methods = {}

        def whitelist(*, methods):
            def register(fn):
                self.allowed_methods[fn] = methods
                return fn
            return register

        self.frappe.whitelist = whitelist
        self.frappe.session = SimpleNamespace(user="Administrator")
        self.frappe.conf = {"developer_mode": False}
        self.frappe.db = Mock()
        self.frappe.db.get_value.return_value = "lumenpos-sales"
        self.frappe.db.exists.return_value = True
        self.frappe.has_permission = Mock(return_value=True)
        self.frappe.get_installed_apps = Mock(return_value=["frappe", "erpnext", "lumenpos", "lumen_reports"])
        self.frappe.PermissionError = PermissionError
        self.frappe.throw = Mock(side_effect=PermissionError)
        self.frappe.get_roles = Mock(return_value=[])
        self.licensing = SimpleNamespace(get_status=Mock(return_value={"status": "licensed"}), STATUS_EXPIRED="expired")
        package = ModuleType("lumen_reports")
        package.__path__ = [str(Path(__file__).resolve().parents[1] / "lumen_reports")]
        package.licensing = self.licensing
        package.starters = Mock()
        www = ModuleType("lumen_reports.www.lumen")
        www.APP_ROLES = {"Lumen Viewer", "Lumen Restricted Viewer", "Lumen Builder", "Lumen Manager", "System Manager"}
        self.modules = patch.dict(sys.modules, {
            "frappe": self.frappe, "lumen_reports": package, "lumen_reports.www.lumen": www,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.api = importlib.import_module("lumen_reports.integrations.lumenpos")
        self.api._frontend_built = Mock(return_value=True)

    def esafepos_api(self, name):
        # Resolve the exact dotted module used by ESAFE POS at runtime.
        module = importlib.import_module("lumen_reports.integrations.esafepos")
        return getattr(module, name)

    def test_existing_pos_contract_and_links_are_preserved(self):
        status = self.api.get_status()
        self.assertEqual(status["contract"], 3)
        self.assertEqual(status["slug"], "lumenpos-sales")
        self.assertEqual(status["embed_url"], "/lumen/embed/lumenpos-sales")
        self.assertTrue(status["reports_api"])
        self.assertTrue(status["can_view"])
        self.assertEqual(status["product"], "Esafe BLABS")
        self.assertTrue(status["pos_installed"])
        self.assertTrue(status["can_read_source"])

    def test_pos_presence_is_checked_on_current_site(self):
        self.frappe.get_installed_apps.return_value = ["frappe", "erpnext", "lumen_reports"]
        self.assertFalse(self.api.get_status()["pos_installed"])

    def test_esafepos_is_recognized_without_legacy_lumenpos(self):
        self.frappe.get_installed_apps.return_value = ["frappe", "erpnext", "esafepos", "lumen_reports"]
        self.assertTrue(self.api.get_status()["pos_installed"])

    def test_esafepos_status_endpoint_resolves_and_preserves_contract(self):
        get_status = self.esafepos_api("get_status")
        self.assertEqual(self.allowed_methods[get_status], ["GET"])
        self.assertEqual(get_status(), self.api.get_status())
        self.frappe.db.set_value.assert_not_called()

    def test_esafepos_setup_endpoint_preserves_existing_dashboard(self):
        ensure = self.esafepos_api("ensure_dashboard")
        self.assertEqual(self.allowed_methods[ensure], ["POST"])
        self.api._create = Mock()
        self.assertEqual(ensure(lang="ar"), self.api.ensure_dashboard(lang="ar"))
        self.api._create.assert_not_called()

    def test_esafepos_setup_forwards_language_and_creation_result(self):
        self.frappe.db.get_value.return_value = None
        self.api._create = Mock(return_value=("dashboard-name", ["Payment Mix"]))
        result = self.esafepos_api("ensure_dashboard")(lang="ar")
        self.api._create.assert_called_once_with("ar")
        self.assertTrue(result["created"])
        self.assertEqual(result["dropped"], ["Payment Mix"])
        self.assertEqual(result["embed_url"], "/lumen/embed/lumenpos-sales")

    def test_esafepos_endpoints_keep_login_and_setup_gates(self):
        get_status = self.esafepos_api("get_status")
        ensure = self.esafepos_api("ensure_dashboard")
        self.frappe.session.user = "Guest"
        for endpoint in (get_status, ensure):
            with self.subTest(endpoint=endpoint.__name__), self.assertRaises(PermissionError):
                endpoint()
        self.frappe.session.user = "Administrator"
        self.frappe.db.get_value.return_value = None
        self.api._create = Mock()
        self.licensing.get_status.return_value = {"status": "expired"}
        self.assertEqual(ensure()["status"], "license_expired")
        self.licensing.get_status.return_value = {"status": "licensed"}
        self.frappe.has_permission.return_value = False
        self.assertEqual(ensure()["status"], "not_permitted")
        self.api._create.assert_not_called()

    def test_new_dashboard_names_installed_pos_manager_roles(self):
        for installed_roles in ({"EsafePOS Manager"}, {"LumenPOS Manager"}, {"EsafePOS Manager", "LumenPOS Manager"}):
            with self.subTest(roles=installed_roles):
                self.frappe.db.exists.side_effect = lambda doctype, name: doctype == "Role" and name in installed_roles
                doc = Mock(name="dashboard")
                self.frappe.new_doc = Mock(return_value=doc)
                self.api.starters.validate_widgets.return_value = ([{"title": "Net Sales"}], [])
                self.api._create("en")
                audience = {
                    call.args[1]["role"] for call in doc.append.call_args_list
                    if call.args[0] == "visible_to_roles"
                }
                self.assertEqual(audience, installed_roles)
                doc.insert.assert_called_once_with()

    def test_invoice_permission_is_independent_of_dashboard_permission(self):
        self.frappe.has_permission.side_effect = lambda doctype, *args, **kwargs: doctype != "POS Invoice"
        status = self.api.get_status()
        self.assertTrue(status["can_view"])
        self.assertFalse(status["can_read_source"])

    def test_missing_invoice_doctype_does_not_check_its_permission(self):
        self.frappe.db.exists.return_value = False
        status = self.api.get_status()
        self.assertEqual(status["reason"], "needs_erpnext")
        self.assertFalse(status["can_read_source"])
        self.assertFalse(any(call.args[0] == "POS Invoice" for call in self.frappe.has_permission.call_args_list))

    def test_guest_is_refused_before_reading_status(self):
        self.frappe.session.user = "Guest"
        with self.assertRaises(PermissionError):
            self.api.get_status()
        self.frappe.get_installed_apps.assert_not_called()

    def test_existing_dashboard_is_never_recreated(self):
        self.api._create = Mock()
        result = self.api.ensure_dashboard()
        self.assertEqual(result["status"], "ready")
        self.assertFalse(result["created"])
        self.api._create.assert_not_called()

    def test_setup_keeps_existing_permission_and_entitlement_gates(self):
        self.frappe.db.get_value.return_value = None
        self.api._create = Mock()
        self.licensing.get_status.return_value = {"status": "expired"}
        self.assertEqual(self.api.ensure_dashboard()["status"], "license_expired")
        self.licensing.get_status.return_value = {"status": "licensed"}
        self.frappe.has_permission.return_value = False
        self.assertEqual(self.api.ensure_dashboard()["status"], "not_permitted")
        self.api._create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
