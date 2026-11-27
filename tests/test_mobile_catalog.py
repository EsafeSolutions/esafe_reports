"""Permission boundaries and report scoping without a live Frappe server."""
import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


class CatalogTests(unittest.TestCase):
    def setUp(self):
        f = self.frappe = ModuleType("frappe")
        f._ = lambda s: s
        f.whitelist = lambda **kwargs: lambda fn: fn
        f.PermissionError = PermissionError
        f.throw = lambda message, error=ValueError: (_ for _ in ()).throw(error(message))
        f.session = SimpleNamespace(user="viewer@example.com")
        f.get_roles = Mock(return_value=["Lumen Viewer"])
        f.has_permission = Mock(return_value=True)
        f.get_list = Mock(return_value=[])
        f.utils = SimpleNamespace(nowdate=lambda: "2026-11-27")
        f.db = SimpleNamespace(get_single_value=Mock(return_value="LKR"))
        model = ModuleType("frappe.model")
        self.allowed = {"name", "item_name", "item_group", "stock_uom", "is_stock_item", "item_code", "price_list_rate", "currency", "uom", "packing_unit", "valid_from", "valid_upto", "warehouse", "actual_qty", "reserved_qty", "ordered_qty", "projected_qty", "posting_date", "pos_profile", "docstatus", "base_net_amount", "stock_qty", "company", "default_currency"}
        model.get_permitted_fields = Mock(side_effect=lambda *a, **kw: list(self.allowed))
        package = ModuleType("lumen_reports")
        package.query_engine = self.engine = SimpleNamespace(execute=Mock(return_value={"labels": ["Groceries"], "values": [25]}))
        integrations = ModuleType("lumen_reports.integrations")
        integrations.lumenpos = self.pos = SimpleNamespace(get_status=Mock(return_value={"can_view": True, "can_read_source": True, "reason": None}))
        patched = patch.dict(sys.modules, {"frappe": f, "frappe.model": model, "lumen_reports": package, "lumen_reports.integrations": integrations})
        patched.start(); self.addCleanup(patched.stop)
        spec = importlib.util.spec_from_file_location("catalog_under_test", Path(__file__).resolve().parents[1] / "lumen_reports/mobile_catalog.py")
        self.catalog = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.catalog)

    def test_guest_and_non_reporting_user_never_read_catalogue(self):
        self.frappe.session.user = "Guest"
        with self.assertRaises(PermissionError): self.catalog.get_products()
        self.frappe.session.user = "staff@example.com"; self.frappe.get_roles.return_value = ["Sales User"]
        with self.assertRaises(PermissionError): self.catalog.get_options()
        self.frappe.get_list.assert_not_called()

    def test_field_level_price_and_stock_restrictions_are_enforced(self):
        self.allowed.remove("price_list_rate")
        with self.assertRaises(PermissionError): self.catalog._prices(["TEA"], "Selling")
        self.allowed.remove("actual_qty")
        with self.assertRaises(PermissionError): self.catalog._stock(["TEA"], "")
        self.frappe.get_list.assert_not_called()

    def test_invalid_pages_and_oversize_inputs_do_not_query(self):
        for offset in (-1, "1.5", True, "01", 1000001):
            with self.subTest(offset=offset), self.assertRaises(ValueError): self.catalog.get_products(start=offset)
        with self.assertRaises(ValueError): self.catalog.get_products(search="a" * 141)
        self.frappe.get_list.assert_not_called()

    def test_unreadable_stock_is_not_reported_as_zero(self):
        self.frappe.get_list.return_value = [{"name": "TEA", "item_name": "Tea", "item_group": "Groceries", "is_stock_item": 1, "stock_uom": "Nos"}]
        self.frappe.has_permission.side_effect = lambda dt, *_: dt != "Bin"
        result = self.catalog.get_products()
        self.assertIsNone(result["items"][0]["actual_qty"])
        self.assertIn("stock", result["errors"])

    def test_stock_drops_inaccessible_warehouses(self):
        self.frappe.get_list.side_effect = [[
            {"item_code": "TEA", "warehouse": "Visible", "actual_qty": 3},
            {"item_code": "TEA", "warehouse": "Hidden", "actual_qty": 90},
        ], [{"name": "Visible"}]]
        stock, partial = self.catalog._stock(["TEA"], "")
        self.assertEqual([r["warehouse"] for r in stock["TEA"]], ["Visible"])
        self.assertFalse(partial)

    def test_price_validity_excludes_future_and_expired_rates_and_preserves_zero(self):
        self.frappe.get_list.side_effect = [[{"name": "Selling"}], [
            {"item_code": "TEA", "price_list_rate": 0, "valid_from": "2026-11-27", "valid_upto": "2026-11-27"},
            {"item_code": "TEA", "price_list_rate": 100, "valid_from": "2026-11-28", "valid_upto": None},
            {"item_code": "TEA", "price_list_rate": 200, "valid_from": None, "valid_upto": "2026-11-26"},
        ]]
        prices, _ = self.catalog._prices(["TEA"], "Selling")
        self.assertEqual([r["price_list_rate"] for r in prices["TEA"]], [0])

    def test_sales_keep_parent_and_item_row_permission_scopes_before_aggregating(self):
        self.frappe.get_list.side_effect = [[{"name": "PERMITTED-INVOICE"}], [{"name": "VISIBLE-ITEM", "item_name": "Tea", "item_group": "Groceries", "stock_uom": "Nos"}]]
        result = self.catalog.get_sales("2026-11-01", "2026-11-27", pos_profile="Outlet")
        self.assertEqual(result["net_sales"], 25)
        self.assertEqual(result["currency"], "LKR")
        parent_query = self.frappe.get_list.call_args_list[0]
        self.assertIn(["docstatus", "=", 1], parent_query.kwargs["filters"])
        self.assertIn(["pos_profile", "=", "Outlet"], parent_query.kwargs["filters"])
        for call in self.engine.execute.call_args_list:
            self.assertIn(["parent", "in", ["PERMITTED-INVOICE"]], call.args[0]["filters"])
            self.assertIn(["item_code", "in", ["VISIBLE-ITEM"]], call.args[0]["filters"])

    def test_sales_refuse_invalid_dates_or_denied_dashboard_before_data_reads(self):
        for first, last in (("2026-12-01", "2026-11-01"), ("2026-02-30", "2026-03-01"), ("2024-01-01", "2026-01-01")):
            with self.subTest(first=first), self.assertRaises(ValueError): self.catalog.get_sales(first, last)
        self.pos.get_status.return_value["can_view"] = False
        with self.assertRaises(PermissionError): self.catalog.get_sales("2026-11-01", "2026-11-27")
        self.frappe.get_list.assert_not_called(); self.engine.execute.assert_not_called()

    def test_aggregate_limit_is_explicitly_reported_as_partial(self):
        self.frappe.get_list.side_effect = [[{"name": "INVOICE"}], [{"name": "TEA"}]]
        self.engine.execute.return_value = {"labels": [str(i) for i in range(500)], "values": [1] * 500}
        self.assertTrue(self.catalog.get_sales("2026-11-01", "2026-11-27")["partial"])

    def test_sales_never_add_different_company_base_currencies(self):
        self.frappe.get_list.side_effect = [[{"name": "A", "company": "LK"}, {"name": "B", "company": "US"}], [{"name": "LK", "default_currency": "LKR"}, {"name": "US", "default_currency": "USD"}]]
        with self.assertRaises(ValueError): self.catalog.get_sales("2026-11-01", "2026-11-27")
        self.engine.execute.assert_not_called()
