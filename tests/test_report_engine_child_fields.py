"""Exercise real catalogue/query/report code against SQLite, without a Frappe site.

Only Frappe's metadata, permissions and database adapter are substituted. PyPika
builds the actual SQL, including invoice allowlists and child-table constraints.
Install tests/requirements.txt in the standalone test environment before running.
"""

import importlib.util
from pathlib import Path
import sqlite3
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from pypika import Order, Query, Table
from pypika.functions import Avg, Count, Max, Min, Sum


class SQLiteAdapter:
    def __init__(self, query, connection, statements):
        self.query, self.connection, self.statements = query, connection, statements

    def __getattr__(self, name):
        def call(*args, **kwargs):
            return SQLiteAdapter(getattr(self.query, name)(*args, **kwargs), self.connection, self.statements)
        return call

    def run(self, as_dict=False):
        sql = self.query.get_sql()
        self.statements.append(sql)
        rows = self.connection.execute(sql).fetchall()
        return [dict(row) for row in rows] if as_dict else rows


class Meta:
    def __init__(self, istable=False, **fields):
        self.istable = istable
        self.fields = {
            name: SimpleNamespace(fieldname=name, label=name, fieldtype=kind, options=options)
            for name, (kind, options) in fields.items()
        }

    def get_field(self, name):
        # Frappe system columns exist in SQL, not as ordinary DocFields.
        return self.fields.get(name)


class ReportEngineChildFieldTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.addCleanup(self.connection.close)
        self.connection.executescript('''
            CREATE TABLE "tabPOS Invoice Item" (
                name TEXT, parent TEXT, parenttype TEXT, parentfield TEXT,
                item_code TEXT, base_net_amount REAL, stock_qty REAL
            );
            CREATE TABLE "tabPOS Invoice" (name TEXT, posting_date TEXT);
            CREATE TABLE "tabItem" (name TEXT, item_group TEXT);
            INSERT INTO "tabPOS Invoice" VALUES ('VISIBLE', '2026-11-27'), ('RETURN', '2026-11-28'), ('HIDDEN', '2026-11-27');
            INSERT INTO "tabItem" VALUES ('TEA', 'Beverages'), ('RICE', 'Groceries');
            INSERT INTO "tabPOS Invoice Item" VALUES
                ('sale', 'VISIBLE', 'POS Invoice', 'items', 'TEA', 100, 2),
                ('return', 'RETURN', 'POS Invoice', 'items', 'TEA', -25, -0.5),
                ('denied-invoice', 'HIDDEN', 'POS Invoice', 'items', 'TEA', 900, 18),
                ('other-parenttype', 'VISIBLE', 'Sales Invoice', 'items', 'TEA', 999, 1000),
                ('denied-item', 'VISIBLE', 'POS Invoice', 'items', 'RICE', 300, 5);
        ''')
        self.statements = []
        self.metadata = {
            "POS Invoice Item": Meta(True, item_code=("Link", "Item"), base_net_amount=("Currency", None), stock_qty=("Float", None)),
            "POS Invoice": Meta(posting_date=("Date", None), pos_profile=("Link", "POS Profile"), company=("Link", "Company")),
            "Item": Meta(item_name=("Data", None), item_group=("Link", "Item Group"), stock_uom=("Link", "UOM")),
        }
        f = self.frappe = ModuleType("frappe")
        f._ = lambda text: text
        f.whitelist = lambda **kwargs: lambda fn: fn
        f.throw = lambda text, error=ValueError: (_ for _ in ()).throw(error(text))
        f.PermissionError = PermissionError
        f.get_meta = lambda doctype: self.metadata[doctype]
        f.has_permission = Mock(return_value=True)
        f.utils = SimpleNamespace(cint=lambda value: int(value or 0))
        f.session = SimpleNamespace(user="viewer@example.com")
        f.get_roles = lambda: ["Lumen Viewer"]
        f.db = SimpleNamespace(get_single_value=lambda *args: "LKR")
        f.get_list = Mock(side_effect=lambda doctype, **kwargs: {
            "POS Invoice": [{"name": "VISIBLE"}, {"name": "RETURN"}],
            "Item": [{"name": "TEA", "item_name": "Tea", "item_group": "Beverages", "stock_uom": "Nos"}],
        }[doctype])
        f.qb = SimpleNamespace(
            DocType=lambda doctype: Table("tab" + doctype),
            from_=lambda table: SQLiteAdapter(Query.from_(table), self.connection, self.statements),
        )
        qb = ModuleType("frappe.query_builder"); qb.Order = Order
        functions = ModuleType("frappe.query_builder.functions")
        for function in (Avg, Count, Max, Min, Sum):
            setattr(functions, function.__name__, function)
        model = ModuleType("frappe.model")
        model.get_permitted_fields = lambda doctype, **kwargs: ["name", "docstatus", *self.metadata[doctype].fields]
        root = Path(__file__).resolve().parents[1]
        package = ModuleType("lumen_reports"); package.__path__ = [str(root / "lumen_reports")]
        integrations = ModuleType("lumen_reports.integrations")
        integrations.lumenpos = SimpleNamespace(get_status=lambda: {"can_view": True, "can_read_source": True, "reason": None})
        modules = patch.dict(sys.modules, {
            "frappe": f, "frappe.model": model, "frappe.query_builder": qb,
            "frappe.query_builder.functions": functions, "lumen_reports": package,
            "lumen_reports.integrations": integrations,
        })
        modules.start(); self.addCleanup(modules.stop)
        for name in ("report_engine", "query_engine", "mobile_catalog"):
            spec = importlib.util.spec_from_file_location("lumen_reports." + name, root / "lumen_reports" / (name + ".py"))
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            setattr(package, name, module)
            spec.loader.exec_module(module)
            setattr(self, name, module)

    def test_category_and_product_sales_execute_with_permitted_invoice_scope(self):
        for grouping, label in (("category", "Beverages"), ("product", "Tea")):
            with self.subTest(grouping=grouping):
                result = self.mobile_catalog.get_sales("2026-11-01", "2026-11-28", group_by=grouping)
                self.assertEqual(result["net_sales"], 75)
                self.assertEqual(result["rows"][0]["label"], label)
                self.assertEqual(result["rows"][0]["quantity"], 1.5)
                self.assertFalse(result["partial"])
        self.assertEqual(len(self.statements), 4)  # amount and quantity for each grouping

    def test_child_system_columns_can_be_selected_and_filtered_without_docfields(self):
        result = self.report_engine.execute({
            "doctype": "POS Invoice Item", "parent_doctype": "POS Invoice",
            "fields": ["parent", "parenttype", "parentfield"],
            "filters": [["parent", "in", ["VISIBLE"]], ["parentfield", "=", "items"], ["item_code", "=", "TEA"]],
        })
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["rows"], [{"c0": "VISIBLE", "c1": "POS Invoice", "c2": "items"}])

    def test_child_system_columns_are_not_accepted_on_parent_doctypes(self):
        resolver = self.report_engine._Resolver("POS Invoice")
        for name in ("parent", "parenttype", "parentfield"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                resolver.column(name)
        self.assertEqual(self.statements, [])

    def test_parent_document_fields_still_use_the_permission_checked_parent_join(self):
        result = self.report_engine.execute({
            "doctype": "POS Invoice Item", "parent_doctype": "POS Invoice",
            "aggregate": {"function": "sum", "field": "base_net_amount"},
            "filters": [["parent", "in", ["VISIBLE", "RETURN"]], ["posting_date", "=", "2026-11-27"], ["item_code", "=", "TEA"]],
        })
        self.assertEqual(result["value"], 100)
        self.frappe.has_permission.assert_any_call("POS Invoice", "read")

    def test_parent_read_permission_is_required_before_query_execution(self):
        self.frappe.has_permission.return_value = False
        with self.assertRaises(PermissionError):
            self.report_engine.execute({"doctype": "POS Invoice Item", "parent_doctype": "POS Invoice", "fields": ["parent"]})
        self.assertEqual(self.statements, [])
