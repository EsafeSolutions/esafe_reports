"""Web Push contracts without a live Frappe database or external push request."""

import base64
from contextlib import nullcontext
import datetime
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

# Load optional native-backed dependencies before patching sys.modules. Reloading
# cryptography's Python curve classes around its cached Rust backend is unsafe.
try:
    import http_ece
    import pywebpush
    import werkzeug
except ImportError:
    pass


class Document(SimpleNamespace):
    def update(self, values):
        self.__dict__.update(values)

    def save(self, **kwargs):
        self.name = getattr(self, "endpoint_hash", "settings")
        return self


class PushTests(unittest.TestCase):
    def setUp(self):
        self.frappe = ModuleType("frappe")
        self.frappe._ = lambda text: text
        self.frappe.whitelist = lambda **kwargs: lambda fn: fn
        self.frappe.parse_json = json.loads
        self.frappe.PermissionError = PermissionError

        def throw(message, error=ValueError):
            raise error(message)

        self.frappe.throw = throw
        self.frappe.session = SimpleNamespace(user="manager@example.test")
        self.frappe.flags = SimpleNamespace(in_migrate=False, in_install=False, in_patch=False)
        self.frappe.db = Mock()
        self.frappe.db.exists.return_value = False
        self.frappe.db.get_value.return_value = True
        self.frappe.get_all = Mock(return_value=[])
        self.frappe.enqueue = Mock()
        self.frappe.log_error = Mock()
        self.frappe.has_permission = Mock(return_value=True)
        self.frappe.cache = Mock(return_value=Mock(get_value=Mock(return_value=None)))
        self.frappe.cache.return_value.lock.side_effect = lambda *args, **kwargs: nullcontext()
        self.frappe.set_user = Mock(side_effect=lambda user: setattr(self.frappe.session, "user", user))
        self.settings = Document(public_key="existing-key", contact="mailto:hello@esafe.lk", save=Mock())
        self.frappe.get_single = Mock(return_value=self.settings)
        self.device = Document(name="device", user="manager@example.test", endpoint="https://fcm.googleapis.com/fcm/send/device-token", enabled=1, sales_alerts=1, daily_summary=1, summary_time="20:00:00", summary_last_date=None, timezone="Asia/Colombo", language="en", db_set=Mock())
        self.frappe.get_doc = Mock(return_value=self.device)
        self.frappe.new_doc = Mock(side_effect=lambda *args: Document())
        self.query_engine = SimpleNamespace(execute=Mock(side_effect=[{"value": 15}, {"value": 2}]))
        package = ModuleType("lumen_reports")
        package.__path__ = [str(Path(__file__).resolve().parents[1] / "lumen_reports")]
        package.query_engine = self.query_engine
        integration = ModuleType("lumen_reports.integrations.lumenpos")
        integration.get_status = Mock(return_value={"can_view": True, "can_read_source": True, "reason": None})
        self.integration = integration
        modules = patch.dict(sys.modules, {"frappe": self.frappe, "lumen_reports": package, "lumen_reports.integrations.lumenpos": integration})
        modules.start()
        self.addCleanup(modules.stop)
        self.api = importlib.import_module("lumen_reports.notifications")
        self.api._secret = Mock(return_value="encrypted-secret-value")
        self.api._set_secret = Mock()
        self.public = base64.urlsafe_b64encode(b"\x04" + b"a" * 64).decode().rstrip("=")
        self.auth = base64.urlsafe_b64encode(b"a" * 16).decode().rstrip("=")
        self.payload = {"endpoint": self.device.endpoint, "keys": {"p256dh": self.public, "auth": self.auth}}

    def test_access_is_rechecked_before_reading_subscription_state(self):
        for status in ({"can_view": False, "can_read_source": True, "reason": None}, {"can_view": True, "can_read_source": False, "reason": None}, {"can_view": True, "can_read_source": True, "reason": "needs_role"}):
            self.integration.get_status.return_value = status
            with self.subTest(status=status), self.assertRaises(PermissionError):
                self.api.get_settings()
        self.frappe.get_single.assert_not_called()

    def test_only_browser_push_services_can_receive_outbound_requests(self):
        self.assertEqual(self.api._validate_subscription(self.payload), (self.device.endpoint, self.public, self.auth))
        for endpoint in ("http://fcm.googleapis.com/send/x", "https://127.0.0.1/send/x", "https://localhost/send/x", "https://fcm.googleapis.com.evil.test/x", "https://fcm.googleapis.com@evil.test/x", "https://fcm.googleapis.com:444/x", "https://fcm.googleapis.com/x#secret"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                self.api._validate_subscription({**self.payload, "endpoint": endpoint})

    def test_subscription_key_lengths_are_validated(self):
        for keys in ({"p256dh": "garbage", "auth": self.auth}, {"p256dh": self.public, "auth": "abc"}, {"p256dh": None, "auth": self.auth}):
            with self.subTest(keys=keys), self.assertRaises(ValueError):
                self.api._validate_subscription({**self.payload, "keys": keys})

    def test_subscription_uses_current_user_and_deterministic_endpoint_name(self):
        result = self.api.subscribe(self.payload, {"summary_time": "21:15", "timezone": "Asia/Colombo", "sales_alerts": False})
        expected_name = hashlib.sha256(self.device.endpoint.encode()).hexdigest()
        self.api._set_secret.assert_called_once_with(self.api.SUBSCRIPTION, expected_name, "auth_key", self.auth)
        self.assertTrue(result["enabled"])
        self.assertFalse(result["sales_alerts"])
        self.assertEqual(result["summary_time"], "21:15")
        self.assertNotIn("auth", result)

    def test_foreign_subscription_cannot_be_read_changed_or_revoked(self):
        self.frappe.db.exists.return_value = True
        self.device.user = "other@example.test"
        for action in (lambda: self.api.get_settings(self.device.endpoint), lambda: self.api.subscribe(self.payload), lambda: self.api.unsubscribe(self.device.endpoint)):
            with self.assertRaises(PermissionError):
                action()
        self.device.db_set.assert_not_called()

    def test_revocation_remains_available_after_reporting_role_is_removed(self):
        self.frappe.db.exists.return_value = True
        self.integration.get_status.side_effect = PermissionError
        self.assertFalse(self.api.unsubscribe(self.device.endpoint)["enabled"])
        self.device.db_set.assert_called_once_with("enabled", 0)
        self.frappe.session.user = "Guest"
        with self.assertRaises(PermissionError):
            self.api.unsubscribe(self.device.endpoint)

    def test_preferences_validate_timezone_time_and_boolean_values(self):
        for prefs in ({"summary_time": "25:00"}, {"summary_time": "20:60"}, {"summary_time": "8:00"}, {"timezone": "Not/AZone"}, {"daily_summary": "false"}):
            with self.subTest(prefs=prefs), self.assertRaises(ValueError):
                self.api._preferences(prefs)

    def test_device_time_normalizes_frappe_time_values(self):
        self.device.summary_time = datetime.timedelta(hours=8, minutes=15)
        self.assertEqual(self.api._device(self.device)["summary_time"], "08:15")

    def test_public_settings_do_not_expose_private_key_or_browser_auth(self):
        result = self.api.get_settings()
        self.assertEqual(set(result), {"configured", "public_key", "device"})
        self.assertNotIn("encrypted-secret", json.dumps(result))

    def test_migration_preserves_an_existing_vapid_identity(self):
        self.api.setup_push()
        self.api._set_secret.assert_not_called()
        self.settings.save.assert_not_called()

    def test_migration_generates_matching_p256_private_and_public_keys(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        self.settings.public_key = ""
        self.api.setup_push()
        raw = self.api._set_secret.call_args.args[3]
        private = ec.derive_private_key(int.from_bytes(base64.urlsafe_b64decode(raw + "="), "big"), ec.SECP256R1())
        public = private.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.assertEqual(base64.urlsafe_b64encode(public).decode().rstrip("="), self.settings.public_key)

    def test_background_delivery_restores_user_even_if_delivery_raises(self):
        self.device.user = "viewer@example.test"
        with self.assertRaises(RuntimeError):
            self.api._as_subscriber("device", Mock(side_effect=RuntimeError("failure")))
        self.assertEqual(self.frappe.session.user, "manager@example.test")
        self.assertEqual([c.args[0] for c in self.frappe.set_user.call_args_list], ["viewer@example.test", "manager@example.test"])

    def test_disabled_users_and_lost_permissions_receive_no_push(self):
        callback = Mock()
        self.frappe.db.get_value.return_value = False
        self.assertFalse(self.api._as_subscriber("device", callback))
        self.frappe.db.get_value.return_value = True
        self.integration.get_status.side_effect = PermissionError
        self.assertFalse(self.api._as_subscriber("device", callback))
        callback.assert_not_called()

    def test_sale_alert_checks_permission_on_the_specific_invoice(self):
        invoice = Document(name="POS-1", docstatus=1, is_return=0)
        self.frappe.get_doc.side_effect = lambda doctype, name: invoice if doctype == "POS Invoice" else self.device
        self.frappe.get_all.return_value = ["device"]
        self.frappe.has_permission.return_value = False
        self.api._send = Mock()
        self.api.deliver_sale("POS-1")
        self.frappe.has_permission.assert_called_once_with("POS Invoice", "read", doc=invoice)
        self.api._send.assert_not_called()

    def test_invoice_submission_queues_after_commit_and_skips_migrations(self):
        self.api.on_invoice_submit(Document(name="POS-1", docstatus=1))
        self.assertTrue(self.frappe.enqueue.call_args.kwargs["enqueue_after_commit"])
        self.frappe.enqueue.reset_mock()
        self.frappe.flags.in_migrate = True
        self.api.on_invoice_submit(Document(name="POS-1", docstatus=1))
        self.frappe.enqueue.assert_not_called()

    def test_summary_rechecks_permissions_and_only_marks_successful_delivery(self):
        self.api._send = Mock(return_value=False)
        self.assertFalse(self.api.deliver_summary("device", "2026-11-26"))
        self.device.db_set.assert_not_called()
        query = self.query_engine.execute.call_args_list[0].args[0]
        self.assertEqual(query["filters"], [["docstatus", "=", 1], ["posting_date", "=", "2026-11-26"]])
        self.query_engine.execute.side_effect = [{"value": 15}, {"value": 2}]
        self.api._send.return_value = True
        self.assertTrue(self.api.deliver_summary("device", "2026-11-26"))
        self.device.db_set.assert_called_once_with("summary_last_date", "2026-11-26", update_modified=False)
        self.assertIn("15 invoices, including 2 returns", self.api._send.call_args.args[2])
        self.device.summary_last_date = "2026-11-26"
        self.query_engine.execute.reset_mock()
        self.assertFalse(self.api.deliver_summary("device", "2026-11-26"))
        self.query_engine.execute.assert_not_called()

    def test_scheduler_respects_device_local_time_and_previous_delivery_date(self):
        self.frappe.get_all.return_value = [self.device]
        self.api._local_now = Mock(return_value=datetime.datetime(2026, 11, 26, 19, 59))
        self.api.send_due_summaries()
        self.frappe.enqueue.assert_not_called()
        self.api._local_now.return_value = datetime.datetime(2026, 11, 26, 20, 0)
        self.api.send_due_summaries()
        self.assertEqual(self.frappe.enqueue.call_args.kwargs["date"], "2026-11-26")
        self.assertNotIn("deduplicate", self.frappe.enqueue.call_args.kwargs)
        self.assertIn("2026-11-26", self.frappe.enqueue.call_args.kwargs["job_id"])
        self.frappe.enqueue.reset_mock()
        self.device.summary_last_date = "2026-11-26"
        self.api.send_due_summaries()
        self.frappe.enqueue.assert_not_called()

    def test_feed_is_scoped_to_the_current_user_and_sent_notifications(self):
        self.api.get_feed()
        self.assertEqual(self.frappe.get_all.call_args.kwargs["filters"], {"user": "manager@example.test", "delivery_status": "Sent"})

    def test_transport_uses_server_secrets_and_disables_expired_endpoints(self):
        class WebPushException(Exception):
            def __init__(self):
                self.response = SimpleNamespace(status_code=410)

        transport = ModuleType("pywebpush")
        transport.WebPushException = WebPushException
        transport.webpush = Mock()
        self.device.p256dh = self.public
        self.api._secret.side_effect = lambda doctype, name, field: self.auth if field == "auth_key" else "server-private-key"
        log = Document(delivery_status="Failed", insert=Mock())
        self.frappe.get_doc.return_value = log
        with patch.dict(sys.modules, {"pywebpush": transport}):
            self.assertTrue(self.api._send(self.device, "Sale", "Open dashboard", "Sale", "sale-1"))
            self.assertEqual(transport.webpush.call_args.kwargs["vapid_private_key"], "server-private-key")
            self.assertEqual(transport.webpush.call_args.kwargs["subscription_info"]["keys"]["auth"], self.auth)
            self.assertEqual(transport.webpush.call_args.kwargs["timeout"], 10)
            transport.webpush.side_effect = WebPushException()
            log.delivery_status = "Failed"
            self.assertFalse(self.api._send(self.device, "Sale", "Open dashboard", "Sale", "sale-2"))
            self.device.db_set.assert_called_once_with("enabled", 0, update_modified=False)
        self.frappe.log_error.assert_not_called()

    def test_service_worker_is_public_and_scoped_only_to_reports(self):
        try:
            import werkzeug  # provided by Frappe; optional in standalone contract checks
        except ImportError:
            self.skipTest("Werkzeug is supplied by the Frappe runtime")
        self.frappe.get_app_path = lambda app, folder: str(Path(__file__).resolve().parents[1] / app / folder)
        worker = importlib.import_module("lumen_reports.pwa").service_worker()
        self.assertEqual(worker.mimetype, "application/javascript")
        self.assertEqual(worker.headers["Service-Worker-Allowed"], "/esafe-report/")
        self.assertIn("no-store", worker.headers["Cache-Control"])
        self.assertNotIn("__LUMEN_BUILD__", worker.get_data(as_text=True))
        self.assertNotIn("csrf_token", worker.get_data(as_text=True))

    def test_generated_vapid_keys_encrypt_real_web_push_payload_without_network(self):
        try:
            import http_ece
            import pywebpush
        except ImportError:
            self.skipTest("Install the declared pywebpush dependency to run transport interoperability")
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        self.settings.public_key = ""
        self.api.setup_push()
        private = self.api._set_secret.call_args.args[3]
        receiver = ec.generate_private_key(ec.SECP256R1())
        receiver_public = receiver.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.device.p256dh = base64.urlsafe_b64encode(receiver_public).decode().rstrip("=")
        self.api._secret.side_effect = lambda doctype, name, field: self.auth if field == "auth_key" else private
        self.frappe.get_doc.return_value = Document(delivery_status="Failed", insert=Mock())
        with patch("requests.post", return_value=SimpleNamespace(status_code=201, headers={}, text="")) as post:
            self.assertTrue(self.api._send(self.device, "Sale", "Encrypted message", "Sale", "sale-test"))
        transmitted = post.call_args.kwargs
        self.assertIn("vapid", transmitted["headers"]["authorization"])
        decrypted = http_ece.decrypt(transmitted["data"], private_key=receiver, auth_secret=b"a" * 16, version="aes128gcm")
        self.assertEqual(json.loads(decrypted)["body"], "Encrypted message")


if __name__ == "__main__":
    unittest.main()
