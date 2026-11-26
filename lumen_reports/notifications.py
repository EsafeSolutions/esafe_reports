# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary

"""Per-device Web Push for the POS dashboard, including background delivery.

Only a browser subscription is accepted from the client. Every delivery runs with
the subscriber's current dashboard and invoice permissions. VAPID private keys
and subscription authentication secrets stay encrypted in Frappe's password store.
"""

import base64
import datetime
import hashlib
import json
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import frappe
from frappe import _

from lumen_reports import query_engine
from lumen_reports.integrations import lumenpos

SUBSCRIPTION = "Lumen Push Subscription"
SETTINGS = "Lumen Push Settings"
LOG = "Lumen Push Log"
APP_URL = "/esafe-report/mobile"
PUSH_HOSTS = ("fcm.googleapis.com", "push.services.mozilla.com", "web.push.apple.com", "notify.windows.com")


def _require_access():
	status = lumenpos.get_status()
	if not (status["can_view"] and status["can_read_source"] and not status["reason"]):
		frappe.throw(_("Open an accessible POS sales dashboard before enabling notifications."), frappe.PermissionError)


def _secret(doctype, name, fieldname):
	from frappe.utils.password import get_decrypted_password

	return get_decrypted_password(doctype, name, fieldname, raise_exception=False)


def _set_secret(doctype, name, fieldname, value):
	from frappe.utils.password import set_encrypted_password

	set_encrypted_password(doctype, name, value, fieldname=fieldname)


def setup_push():
	"""Install/migrate only: create a site's VAPID identity once, never rotate it."""
	from cryptography.hazmat.primitives import serialization
	from cryptography.hazmat.primitives.asymmetric import ec

	settings = frappe.get_single(SETTINGS)
	if settings.public_key:
		return
	key = ec.generate_private_key(ec.SECP256R1())
	private = base64.urlsafe_b64encode(key.private_numbers().private_value.to_bytes(32, "big")).decode("ascii").rstrip("=")
	public = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
	_set_secret(SETTINGS, SETTINGS, "private_key", private)
	settings.public_key = base64.urlsafe_b64encode(public).decode("ascii").rstrip("=")
	settings.contact = settings.contact or "mailto:hello@esafe.lk"
	settings.save(ignore_permissions=True)  # migration owns this site-wide identity


def _owned(endpoint):
	name = hashlib.sha256(str(endpoint).encode()).hexdigest()
	if not frappe.db.exists(SUBSCRIPTION, name):
		return None
	doc = frappe.get_doc(SUBSCRIPTION, name)
	if doc.user != frappe.session.user:
		frappe.throw(_("This device is registered to a different account."), frappe.PermissionError)
	return doc


def _key(value, length):
	if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", value):
		frappe.throw(_("The browser returned an invalid push subscription."))
	try:
		decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
	except (ValueError, TypeError):
		frappe.throw(_("The browser returned an invalid push subscription."))
	if len(decoded) != length or (length == 65 and decoded[0] != 4):
		frappe.throw(_("The browser returned an invalid push subscription."))
	return value.rstrip("=")


def _validate_subscription(raw):
	raw = frappe.parse_json(raw) if isinstance(raw, str) else raw
	if not isinstance(raw, dict) or not isinstance(raw.get("keys"), dict):
		frappe.throw(_("The browser returned an invalid push subscription."))
	endpoint = raw.get("endpoint")
	if not isinstance(endpoint, str) or len(endpoint) > 2048:
		frappe.throw(_("Invalid notification endpoint."))
	try:
		url = urlsplit(endpoint)
		allowed = any(url.hostname == host or (url.hostname or "").endswith("." + host) for host in PUSH_HOSTS)
		valid = url.scheme == "https" and url.port in (None, 443) and not (url.username or url.password or url.fragment)
	except ValueError:
		valid = allowed = False
	if not valid or not allowed:
		frappe.throw(_("This browser's push service is not supported."))
	return endpoint, _key(raw["keys"].get("p256dh"), 65), _key(raw["keys"].get("auth"), 16)


def _preferences(raw):
	raw = frappe.parse_json(raw) if isinstance(raw, str) else (raw or {})
	if not isinstance(raw, dict):
		frappe.throw(_("Notification preferences must be an object."))
	zone = str(raw.get("timezone") or "Asia/Colombo")
	try:
		ZoneInfo(zone)
	except (ZoneInfoNotFoundError, ValueError):
		frappe.throw(_("Choose a valid time zone."))
	at = str(raw.get("summary_time") or "20:00")
	if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", at):
		frappe.throw(_("Choose a valid daily summary time."))
	for key in ("sales_alerts", "daily_summary"):
		if key in raw and raw[key] not in (True, False, 0, 1):
			frappe.throw(_("Invalid notification preference."))
	return {
		"sales_alerts": int(bool(raw.get("sales_alerts", True))),
		"daily_summary": int(bool(raw.get("daily_summary", True))),
		"summary_time": at + ":00",
		"timezone": zone,
		"language": "ar" if raw.get("language") == "ar" else "en",
	}


def _device(doc):
	if not doc:
		return None
	return {
		"enabled": bool(doc.enabled),
		"sales_alerts": bool(doc.sales_alerts),
		"daily_summary": bool(doc.daily_summary),
		"summary_time": _summary_clock(doc.summary_time),
		"timezone": doc.timezone,
		"language": doc.language,
	}


def _summary_clock(value):
	hour, minute = (int(part) for part in str(value or "20:00").split(":")[:2])
	return f"{hour:02d}:{minute:02d}"


@frappe.whitelist(methods=["GET"])
def get_settings(endpoint=None):
	_require_access()
	settings = frappe.get_single(SETTINGS)
	return {
		"configured": bool(settings.public_key and _secret(SETTINGS, SETTINGS, "private_key")),
		"public_key": settings.public_key or "",
		"device": _device(_owned(endpoint)) if endpoint else None,
	}


@frappe.whitelist(methods=["POST"])
def subscribe(subscription, preferences=None):
	_require_access()
	settings = frappe.get_single(SETTINGS)
	if not settings.public_key or not _secret(SETTINGS, SETTINGS, "private_key"):
		frappe.throw(_("Notifications are not configured on this site yet. Ask your administrator to migrate the reports app."))
	endpoint, public, auth = _validate_subscription(subscription)
	prefs = _preferences(preferences)
	doc = _owned(endpoint)
	if not doc:
		doc = frappe.new_doc(SUBSCRIPTION)
		doc.endpoint_hash = hashlib.sha256(endpoint.encode()).hexdigest()
		doc.user = frappe.session.user
	doc.endpoint = endpoint
	doc.p256dh = public
	doc.enabled = 1
	doc.update(prefs)
	doc.save(ignore_permissions=True)  # authenticated caller may manage only their own device
	_set_secret(SUBSCRIPTION, doc.name, "auth_key", auth)
	return _device(doc)


@frappe.whitelist(methods=["POST"])
def unsubscribe(endpoint):
	# Revocation still works after a user's reporting role has been removed.
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in"), frappe.PermissionError)
	doc = _owned(endpoint)
	if doc:
		doc.db_set("enabled", 0)
	return {"enabled": False}


@frappe.whitelist(methods=["GET"])
def get_feed():
	_require_access()
	return frappe.get_all(
		LOG, filters={"user": frappe.session.user, "delivery_status": "Sent"},
		fields=["name", "title", "body", "kind", "creation"], order_by="creation desc", limit_page_length=30,
	)


@frappe.whitelist(methods=["POST"])
def send_test(endpoint):
	_require_access()
	doc = _owned(endpoint)
	if not doc or not doc.enabled:
		frappe.throw(_("Enable notifications on this device first."))
	# A short per-user cooldown prevents accidental double taps and push spam.
	cache = frappe.cache()
	key = "lumen_push_test:" + frappe.session.user
	if cache.get_value(key):
		frappe.throw(_("Wait a minute before sending another test."))
	cache.set_value(key, 1, expires_in_sec=60)
	frappe.enqueue("lumen_reports.notifications.deliver_test", name=doc.name, enqueue_after_commit=True)
	return {"queued": True}


def _send(doc, title, body, kind, tag):
	from pywebpush import WebPushException, webpush

	settings = frappe.get_single(SETTINGS)
	private = _secret(SETTINGS, SETTINGS, "private_key")
	auth = _secret(SUBSCRIPTION, doc.name, "auth_key")
	if not private or not auth or not doc.enabled:
		return False
	# Revalidate persisted endpoints before any outbound request, including old records.
	endpoint, public, auth = _validate_subscription({"endpoint": doc.endpoint, "keys": {"p256dh": doc.p256dh, "auth": auth}})
	log = frappe.get_doc({
		"doctype": LOG, "user": doc.user, "subscription": doc.name, "title": title,
		"body": body, "kind": kind, "delivery_status": "Failed",
	})
	try:
		webpush(
			subscription_info={"endpoint": endpoint, "keys": {"p256dh": public, "auth": auth}},
			data=json.dumps({"title": title, "body": body, "url": APP_URL, "tag": tag}),
			vapid_private_key=private, vapid_claims={"sub": settings.contact or "mailto:hello@esafe.lk"},
			ttl=3600, timeout=10,
		)
		log.delivery_status = "Sent"
	except WebPushException as exc:
		if getattr(getattr(exc, "response", None), "status_code", None) in (404, 410):
			doc.db_set("enabled", 0, update_modified=False)
		# Push exceptions can contain endpoint credentials. Never log their text.
	except Exception:
		pass
	log.insert(ignore_permissions=True)
	return log.delivery_status == "Sent"


def _as_subscriber(name, callback):
	previous = frappe.session.user
	try:
		doc = frappe.get_doc(SUBSCRIPTION, name)
		if not doc.enabled or not frappe.db.get_value("User", doc.user, "enabled"):
			return False
		frappe.set_user(doc.user)  # deliver with the subscriber's current permissions
		try:
			_require_access()
		except frappe.PermissionError:
			return False
		return callback(doc)
	finally:
		frappe.set_user(previous)


def deliver_test(name):
	return _as_subscriber(name, lambda doc: _send(
		doc, "Esafe BLABS", "Notifications are working on this device.", "Test", "lumen-test",
	))


def on_invoice_submit(doc, method=None):
	if doc.docstatus != 1 or frappe.flags.in_migrate or frappe.flags.in_install or frappe.flags.in_patch:
		return
	frappe.enqueue(
		"lumen_reports.notifications.deliver_sale", invoice_name=doc.name,
		enqueue_after_commit=True, queue="short",
	)


def deliver_sale(invoice_name):
	invoice = frappe.get_doc("POS Invoice", invoice_name)
	if invoice.docstatus != 1:
		return
	for name in frappe.get_all(SUBSCRIPTION, filters={"enabled": 1, "sales_alerts": 1}, pluck="name"):
		def deliver(doc):
			if not frappe.has_permission("POS Invoice", "read", doc=invoice):
				return False
			is_return = bool(invoice.is_return)
			if doc.language == "ar":
				title = "مرتجع جديد" if is_return else "عملية بيع جديدة"
				body = "افتح لوحة المبيعات للاطلاع على آخر الأرقام."
			else:
				title = "New POS return" if is_return else "New POS sale"
				body = "Open your sales dashboard to see the latest figures."
			# Keep invoice/customer identifiers and amounts off the lock screen.
			return _send(doc, title, body, "Return" if is_return else "Sale", "lumen-sale-" + invoice.name)
		try:
			_as_subscriber(name, deliver)
		except Exception:
			frappe.log_error(title="Esafe BLABS push delivery failed", message="A sale alert could not be delivered.")


def _local_now(doc, now):
	return now.astimezone(ZoneInfo(doc.timezone or "Asia/Colombo"))


def send_due_summaries():
	"""Five-minute scheduler tick. Time and day are local to each subscribed device."""
	now = datetime.datetime.now(datetime.timezone.utc)
	for doc in frappe.get_all(
		SUBSCRIPTION, filters={"enabled": 1, "daily_summary": 1},
		fields=["name", "timezone", "summary_time", "summary_last_date"],
	):
		try:
			local = _local_now(doc, now)
			date = local.date().isoformat()
			at = str(doc.summary_time or "20:00")
			# Frappe may return a timedelta, whose single-digit hour is not zero-padded.
			hour, minute = (int(part) for part in at.split(":")[:2])
			if (local.hour, local.minute) < (hour, minute) or str(doc.summary_last_date or "") == date:
				continue
			frappe.enqueue(
				"lumen_reports.notifications.deliver_summary", name=doc.name, date=date,
				job_id=f"lumen_push_summary_{doc.name}_{date}", enqueue_after_commit=True,
			)
		except (ZoneInfoNotFoundError, ValueError):
			continue


def deliver_summary(name, date):
	def deliver(doc):
		if not doc.daily_summary or str(doc.summary_last_date or "") == date:
			return False
		# Query the viewer's own POS Invoice rows through the same engine as widgets.
		filters = [["docstatus", "=", 1], ["posting_date", "=", date]]
		invoices = query_engine.execute({"doctype": "POS Invoice", "aggregate": {"function": "count"}, "filters": filters})
		returns = query_engine.execute({"doctype": "POS Invoice", "aggregate": {"function": "count"}, "filters": [*filters, ["is_return", "=", 1]]})
		count, returned = int(invoices["value"]), int(returns["value"])
		if doc.language == "ar":
			title, body = "ملخص المبيعات اليومي", f"{date}: {count} فاتورة، منها {returned} مرتجع. افتح لوحة المبيعات لعرض التفاصيل."
		else:
			title, body = "Your daily sales summary", f"{date}: {count} invoices, including {returned} returns. Open your dashboard for sales totals."
		if _send(doc, title, body, "Summary", "lumen-summary-" + date):
			doc.db_set("summary_last_date", date, update_modified=False)
			return True
		return False
	# Redis serializes a device/date across scheduler ticks. This also supports
	# Frappe v14, which forwards an unknown `deduplicate` kwarg into the worker.
	with frappe.cache().lock(f"lumen_push_summary:{name}:{date}", timeout=300, blocking_timeout=1):
		return _as_subscriber(name, deliver)


def cleanup_logs():
	cutoff = frappe.utils.add_days(frappe.utils.nowdate(), -30)
	for name in frappe.get_all(LOG, filters={"creation": ["<", cutoff]}, pluck="name", limit_page_length=1000):
		frappe.delete_doc(LOG, name, ignore_permissions=True)
