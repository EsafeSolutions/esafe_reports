"""Read-only mobile catalogue, stock and category sales using the viewer's permissions."""

import datetime
from collections import defaultdict

import frappe
from frappe import _
from frappe.model import get_permitted_fields

from lumen_reports import query_engine
from lumen_reports.integrations import lumenpos

PAGE_SIZE = 20
MAX_SCOPE = 20000
APP_ROLES = {"System Manager", "Lumen Manager", "Lumen Builder", "Lumen Viewer", "Lumen Restricted Viewer"}


def _access():
	if frappe.session.user == "Guest" or (
		frappe.session.user != "Administrator" and not APP_ROLES.intersection(frappe.get_roles())
	):
		frappe.throw(_("You need reporting access to use this app."), frappe.PermissionError)


def _read(doctype, fields, parent=None):
	if not frappe.has_permission(parent or doctype, "read"):
		frappe.throw(_("Not permitted to read {0}").format(parent or doctype), frappe.PermissionError)
	permitted = set(get_permitted_fields(doctype, parenttype=parent, permission_type="read"))
	if not set(fields).issubset(permitted):
		frappe.throw(_("Your permissions do not include the required {0} fields.").format(doctype), frappe.PermissionError)


def _text(value, label="filter"):
	if value is None:
		return ""
	if not isinstance(value, str) or len(value) > 140:
		frappe.throw(_("Choose a valid {0}.").format(label))
	return value.strip()


def _start(value):
	try:
		offset = int(value)
		if str(offset) != str(value) or offset < 0 or offset > 1000000:
			raise ValueError
		return offset
	except (TypeError, ValueError, OverflowError):
		frappe.throw(_("Invalid page."))


def _range(first, last):
	try:
		a, b = datetime.date.fromisoformat(first), datetime.date.fromisoformat(last)
		if a > b or a.isoformat() != first or b.isoformat() != last or (b - a).days > 366:
			raise ValueError
	except (ValueError, TypeError):
		frappe.throw(_("Choose a valid date range of up to one year."))


def _options(doctype, fields, filters=None):
	_read(doctype, fields)
	return frappe.get_list(doctype, fields=fields, filters=filters or [], order_by="name asc", limit_page_length=201)


@frappe.whitelist(methods=["GET"])
def get_options():
	_access()
	result = {"categories": [], "warehouses": [], "price_lists": [], "errors": {}}
	for key, doctype, fields, filters in (
		("categories", "Item Group", ["name"], []),
		("warehouses", "Warehouse", ["name"], [["is_group", "=", 0], ["disabled", "=", 0]]),
		("price_lists", "Price List", ["name", "currency"], [["selling", "=", 1], ["enabled", "=", 1]]),
	):
		try:
			rows = _options(doctype, fields, filters)
			result[key] = rows[:200]
			if len(rows) > 200:
				result["errors"][key] = _("The first 200 available choices are shown.")
		except frappe.PermissionError:
			result["errors"][key] = _("You do not have permission to view these choices.")
	return result


def _prices(codes, price_list):
	fields = ["item_code", "price_list_rate", "currency", "uom", "packing_unit", "valid_from", "valid_upto"]
	_read("Item Price", fields)
	_read("Price List", ["name"])
	if not frappe.get_list("Price List", filters={"name": price_list, "selling": 1, "enabled": 1}, fields=["name"], limit_page_length=1):
		frappe.throw(_("Choose an available selling price list."), frappe.PermissionError)
	today = datetime.date.fromisoformat(str(frappe.utils.nowdate()))
	rows = frappe.get_list("Item Price", fields=fields, filters={"item_code": ["in", codes], "price_list": price_list, "selling": 1, "customer": ["is", "not set"], "supplier": ["is", "not set"], "batch_no": ["is", "not set"]}, order_by="valid_from desc, modified desc", limit_page_length=501)
	prices = defaultdict(list)
	for row in rows[:500]:
		if any(row.get(key) and ((datetime.date.fromisoformat(str(row[key])) > today) if key == "valid_from" else (datetime.date.fromisoformat(str(row[key])) < today)) for key in ("valid_from", "valid_upto")):
			continue
		prices[row["item_code"]].append(row)
	return prices, len(rows) > 500


def _stock(codes, warehouse):
	fields = ["item_code", "warehouse", "actual_qty", "reserved_qty", "ordered_qty", "projected_qty"]
	_read("Bin", fields)
	_read("Warehouse", ["name"])
	filters = {"item_code": ["in", codes]}
	if warehouse:
		if not frappe.get_list("Warehouse", fields=["name"], filters={"name": warehouse}, limit_page_length=1):
			frappe.throw(_("Choose an available warehouse."), frappe.PermissionError)
		filters["warehouse"] = warehouse
	rows = frappe.get_list("Bin", fields=fields, filters=filters, order_by="item_code asc, warehouse asc", limit_page_length=1001)
	warehouses = list({r["warehouse"] for r in rows})
	visible = {r["name"] for r in frappe.get_list("Warehouse", fields=["name"], filters={"name": ["in", warehouses]}, limit_page_length=1001)} if warehouses else set()
	stock = defaultdict(list)
	for row in rows[:1000]:
		if row["warehouse"] in visible:
			stock[row["item_code"]].append(row)
	return stock, len(rows) > 1000


@frappe.whitelist(methods=["GET"])
def get_products(search="", category="", price_list="", warehouse="", start=0, item_code=""):
	_access()
	search, category, price_list, warehouse, item_code = (_text(v) for v in (search, category, price_list, warehouse, item_code))
	offset = _start(start)
	fields = ["name", "item_name", "item_group", "stock_uom", "is_stock_item"]
	_read("Item", fields)
	filters = [["disabled", "=", 0]]
	if category:
		filters.append(["item_group", "=", category])
	if item_code:
		filters.append(["name", "=", item_code])
	or_filters = []
	if search:
		or_filters = [["item_name", "like", f"%{search}%"], ["name", "like", f"%{search}%"]]
		# Joining the barcode child through Item keeps Item row permissions in force.
		matches = frappe.get_list("Item", fields=["name"], filters=filters + [["Item Barcode", "barcode", "=", search]], limit_page_length=20)
		if matches:
			or_filters.append(["name", "in", [r["name"] for r in matches]])
	rows = frappe.get_list("Item", fields=fields, filters=filters, or_filters=or_filters, order_by="item_name asc, name asc", limit_start=offset, limit_page_length=PAGE_SIZE + 1)
	items, more = rows[:PAGE_SIZE], len(rows) > PAGE_SIZE
	codes = [r["name"] for r in items]
	errors, prices, stock, partial = {}, {}, {}, False
	if codes and price_list:
		try:
			prices, capped = _prices(codes, price_list)
			partial |= capped
		except frappe.PermissionError:
			errors["prices"] = _("Prices are unavailable with your current permissions.")
	if codes:
		try:
			stock, capped = _stock(codes, warehouse)
			partial |= capped
		except frappe.PermissionError:
			errors["stock"] = _("Stock is unavailable with your current permissions.")
	for item in items:
		item["prices"] = prices.get(item["name"], [])
		item["stock"] = stock.get(item["name"], [])
		item["actual_qty"] = sum(float(r["actual_qty"] or 0) for r in item["stock"]) if item["is_stock_item"] and "stock" not in errors and not partial else None
	return {"items": items, "start": offset, "limit": PAGE_SIZE, "has_more": more, "errors": errors, "partial": partial, "warehouse": warehouse, "price_list": price_list}


@frappe.whitelist(methods=["GET"])
def get_sales(from_date, to_date, pos_profile="", category="", group_by="category"):
	_access()
	_range(from_date, to_date)
	pos_profile, category = _text(pos_profile), _text(category)
	if group_by not in ("category", "product"):
		frappe.throw(_("Choose category or product sales."))
	status = lumenpos.get_status()
	if not (status["can_view"] and status["can_read_source"] and not status["reason"]):
		frappe.throw(_("You do not have permission to view POS sales."), frappe.PermissionError)
	_read("POS Invoice", ["name", "posting_date", "pos_profile", "docstatus", "company"])
	_read("POS Invoice Item", ["item_code", "base_net_amount", "stock_qty"], parent="POS Invoice")
	_read("Item", ["name", "item_name", "item_group", "stock_uom"])
	filters = [["docstatus", "=", 1], ["posting_date", "between", [from_date, to_date]]]
	if pos_profile:
		filters.append(["pos_profile", "=", pos_profile])
	# Build explicit permission-filtered scopes before the aggregation engine joins.
	parents = frappe.get_list("POS Invoice", fields=["name", "company"], filters=filters, order_by="name asc", limit_page_length=MAX_SCOPE + 1)
	currency = frappe.db.get_single_value("Global Defaults", "default_currency") or ""
	companies = sorted({r["company"] for r in parents if r.get("company")})
	if companies:
		_read("Company", ["name", "default_currency"])
		visible_companies = frappe.get_list("Company", fields=["name", "default_currency"], filters={"name": ["in", companies]}, limit_page_length=MAX_SCOPE + 1)
		if {r["name"] for r in visible_companies} != set(companies):
			frappe.throw(_("You need read access to the companies in this report."), frappe.PermissionError)
		currencies = {r["default_currency"] for r in visible_companies}
		if len(currencies) != 1:
			frappe.throw(_("Select an outlet belonging to one company currency."))
		currency = currencies.pop()
	items = frappe.get_list("Item", fields=["name", "item_name", "item_group", "stock_uom"], filters={"item_group": category} if category else {}, order_by="name asc", limit_page_length=MAX_SCOPE + 1)
	partial = len(parents) > MAX_SCOPE or len(items) > MAX_SCOPE
	rows = {}
	if parents and items:
		group = {"field": "item_group", "via": {"link_field": "item_code", "doctype": "Item"}} if group_by == "category" else {"field": "item_code"}
		visible_codes = [r["name"] for r in items[:MAX_SCOPE]]
		for start in range(0, min(len(parents), MAX_SCOPE), 1000):
			query = {"doctype": "POS Invoice Item", "parent_doctype": "POS Invoice", "group_by": group, "filters": [["parent", "in", [r["name"] for r in parents[start:start + 1000]]], ["item_code", "in", visible_codes]]}
			for metric, field in (("amount", "base_net_amount"), ("quantity", "stock_qty")):
				result = query_engine.execute({**query, "aggregate": {"function": "sum", "field": field}})
				partial |= len(result["labels"]) >= 500
				for label, value in zip(result["labels"], result["values"]):
					row = rows.setdefault(label or "", {"key": label or "", "amount": 0, "quantity": 0})
					row[metric] += float(value or 0)
	lookup = {r["name"]: r for r in items}
	for row in rows.values():
		item = lookup.get(row["key"], {}) if group_by == "product" else {}
		row.update({"label": item.get("item_name") or row["key"] or _("Uncategorized"), "uom": item.get("stock_uom", "")})
	return {"rows": sorted(rows.values(), key=lambda r: (-r["amount"], r["key"])), "currency": currency, "partial": partial, "group_by": group_by, "net_sales": sum(r["amount"] for r in rows.values())}
