# Esafe BLABS mobile app

The POS dashboard is installable from the website on Android and iPhone. It uses
the existing Frappe sign-in, dashboard audience and invoice permissions. Its launch
page is `/esafe-report/mobile`; `/lumen/mobile` also opens the interface.

## Use it

1. Open `/esafe-report/mobile` on the POS site and sign in with your reporting user.
   A signed-out launch returns to this page after the normal Frappe login.
2. If setup is offered, a reporting builder/manager creates the sales dashboard.
3. Open **Settings → Install app**. On Android, accept the installation prompt or
   use the browser menu. On iPhone, use **Safari → Share → Add to Home Screen** and
   open the installed app from its icon.
4. Open **Alerts → Enable notifications** and allow the device's notification
   prompt. Both new-sale/return alerts and the daily summary start enabled. Change
   the switches or summary time as needed. Use **Send test notification** to check
   delivery on that device.

The summary defaults to 20:00 in the device's time zone. It includes the day's
invoice and return counts and opens the dashboard for sales totals. Sales alerts
avoid invoice/customer identifiers and amounts on the lock screen. The Alerts feed
contains successfully dispatched notifications for the signed-in user.

An iPhone needs iOS 16.4 or newer and must open the installed Home Screen app before
requesting push permission. This is an Apple platform requirement, not a setting
the site can turn on silently. See [Apple's Web Push guidance](https://webkit.org/blog/13878/).
Android installation and notification availability depend on the browser and device.

## Deploy this update

Deploy the **reports** app to the same Frappe site as ESAFE POS. The existing POS
compatibility fixes in `integrations/esafepos.py` are required too.

For a self-hosted bench, update the reports checkout to this release through the
normal deployment process, then from the bench directory:

```sh
bench setup requirements --python
bench build --app lumen_reports
bench --site osaka.cloud.esafe.lk migrate
bench --site osaka.cloud.esafe.lk clear-cache
bench --site osaka.cloud.esafe.lk enable-scheduler
bench restart
```

Replace the site name for another installation. Frappe Cloud should install the
release's Python requirements, build assets, run migrations and restart workers
through its normal deployment workflow. Ensure its scheduler and background workers
are enabled. No Frappe Cloud deployment was performed by the local implementation.

After migration, each site receives its own VAPID key pair automatically; subsequent
migrations preserve it. No Firebase account, browser API secret, app-store account
or separate mobile server is needed. Push traffic goes to the device browser's
push service using the [pywebpush library](https://pypi.org/project/pywebpush/).
Outbound HTTPS to the supported browser push providers must work from the bench.

Confirm these URLs on the live HTTPS site:

- `/esafe-report/mobile` opens the mobile dashboard after sign-in.
- `/assets/lumen_reports/pwa/manifest.webmanifest` returns the install manifest.
- `/api/method/lumen_reports.pwa.service_worker` returns JavaScript with
  `Service-Worker-Allowed: /esafe-report/` and is not cached by a reverse proxy.

Then verify installation on a real Android device and iPhone, enable notifications,
close the app, submit an authorized test sale/return, and receive both alerts. Set a
nearby summary time and verify its date and figures. The scheduler checks every
five minutes, so delivery is not guaranteed at the exact chosen minute. OS Focus,
notification settings, connectivity and push-provider delivery can affect arrival.

## Behavior and data handling

- **Overview:** submitted POS invoice metrics from the existing saved dashboard,
  date presets, searchable outlets and a sales trend. Missing or denied metrics show
  a dash rather than a fabricated zero. The trend uses the saved widget's grain;
  a daily widget with one day produces one point, not invented hourly figures.
- **Reports:** existing dashboard charts, tables and CSV/image exports with the
  same filters. Existing dashboard customizations are preserved.
- **Live data:** permission-checked widget requests, realtime invalidation and a
  45-second refresh while the app is visible. Reopening refreshes figures.
- **Alerts:** per-device preferences and a user-scoped feed. Device permission is
  requested only after a tap. Revocation remains possible after a reporting role
  is removed. Expired push subscriptions are disabled after provider 404/410 replies.
- **Daily summaries:** background queries run as the recipient, use submitted POS
  invoices only, respect the stored device time zone and skip already sent dates.
  Counts reflect the ERP's `posting_date`; the scheduled delivery time uses the
  device's selected time zone.
- **Permissions:** delivery rechecks enabled user status, dashboard audience, source
  read permission and, for sale alerts, the specific invoice's read permission.
  No roles are granted automatically.
- **Storage:** VAPID private keys and device authentication keys use Frappe's encrypted
  password store. Notification logs retain 30 days. The service worker caches only
  public static assets and a generic offline page, never authenticated HTML or API
  responses. Live sales require an internet connection.
- **Scope:** the worker controls only `/esafe-report/`, leaving the POS till and
  Frappe Desk outside its scope. Installation always launches the canonical mobile
  page, including when the user initially arrived through the `/lumen` alias.

The new DocTypes are `Lumen Push Settings` (site VAPID identity), `Lumen Push
Subscription` (one device, owner and preferences), and `Lumen Push Log` (delivery
feed). Subscription/log records have no general role CRUD permissions; the scoped
endpoints manage them. `notifications.on_invoice_submit` queues after commit;
`send_due_summaries` runs every five minutes; `cleanup_logs` runs daily.

## Validation and design

The production frontend builds with `cd frontend` then `npm run build`. Run
`python -m unittest discover -s tests -v` and `npm test` for the standalone contract
checks. With Playwright and Chrome available, `node tests/mobile-browser.mjs` from
`frontend` tests the built bundle against `mobile-fixture.mjs`. Fixtures never enter
the shipped app or contact production. Set `PLAYWRIGHT_MODULE` if the package is
provided outside the project. The native browser push subscription is simulated in
that flow; device delivery requires the live-device checks above.

The [design concept](design/mobile-app-concept.png) was generated with the built-in
image generator. Its prompt specified complete Overview, Alerts and Settings
screens, existing brand colors, Plus Jakarta Sans, bottom navigation, touch controls,
installation instructions, new sales/returns and daily summaries. No generated
bitmap is used as application UI. The app uses the repository's existing logo,
code-native controls and data-driven charts.

See [visual verification](design/mobile-app-verification.md) for the rendered
screenshots, comparison points and the browser-verification limit.
