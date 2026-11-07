# ESAFE REPORT + ESAFE POS

ESAFE REPORT is the branded reporting interface in this repository. It shares the
POS site's Frappe session and reads its submitted POS invoices. No remote database
connection or browser API secret is required.

## Install on the POS site

Deploy this checkout through your existing bench or Frappe Cloud deployment process.
The reporting app and ESAFE POS must be installed on the **same site**, alongside
ERPNext. This app declares Frappe 14–16 support; PDF generation needs the existing
WeasyPrint support described in the main README.

After this version has been published to the repository, a new bench installation is:

```sh
bench get-app https://github.com/EsafeSolutions/esafe_reports.git
bench --site your-pos-site install-app lumen_reports
bench build --app lumen_reports
bench --site your-pos-site migrate
bench --site your-pos-site clear-cache
```

For a site that already has `lumen_reports`, update its checkout through the usual
deployment process, build, migrate and clear the cache. Do not install a second copy.
The repository name is `esafe_reports`; the Python/Frappe app name remains
`lumen_reports` because the installed POS checks that exact identifier.
Bench's [get-app implementation](https://github.com/frappe/bench/blob/develop/bench/app.py)
resolves the app's Python package name during installation.

## Connect the dashboard

1. Sign in as Administrator, System Manager, or a reporting builder/manager.
2. Open `/esafe-report/pos` and choose **Set up sales dashboard**. Setup is explicit,
   repeatable and preserves any existing dashboard and customizations.
3. Open `/pos#insights` and select **Sales dashboard**. The POS remembers the last
   Insights tab, so you may need to select it manually.
4. If Insights is hidden, enable Insights in the POS settings and use a POS manager account.

The dashboard includes net sales, invoice count, average basket, returns, daily sales,
sales by outlet and cashier, payment mix, top items and busy hours. Its filters cover
dates, outlets, customers, items and payment methods. The backend omits charts whose
required data cannot be read during setup and reports those omissions.

## Access

- Setup requires `Lumen Builder`, `Lumen Manager`, or `System Manager` and the
  existing reporting entitlement rules.
- A POS manager can use `Lumen Restricted Viewer` plus the existing `LumenPOS Manager`
  role to see the POS dashboard without exposing unrelated dashboards. ESAFE POS
  retains that technical role name.
- Read access to `POS Invoice` and the linked records used by each chart is still
  required. The connection screen checks base invoice access; individual chart
  queries enforce their own linked-record permissions.
- No role is automatically granted, and existing dashboards' audiences are unchanged.
- Existing reports remain readable when a subscription expires; setup still respects
  the original entitlement check.

## Compatibility

The POS continues to call `lumen_reports.integrations.lumenpos.get_status` (GET) and
`lumen_reports.integrations.lumenpos.ensure_dashboard` (POST). Contract version 3,
dashboard slug `lumenpos-sales`, and registered-report endpoints are unchanged.
Status now also returns `product`, `pos_installed`, and `can_read_source` for the
ESAFE REPORT connection screen. These fields do not widen access.

Both `/esafe-report/...` and `/lumen/...` serve the same frontend. Existing POS embeds
at `/lumen/embed/lumenpos-sales` keep working, including language and theme parameters.
Submitted POS invoices are the single source of sales data, avoiding double counting
after a register close consolidates them into Sales Invoices.

## Verify a deployment

Open `/esafe-report/pos`, then verify the embedded dashboard as an authorized POS
manager. Compare a known date/outlet to the POS invoice totals, including a return.
Verify that an unauthorized user cannot view the dashboard or its invoice data.

Local checks (no Frappe site needed):

```sh
cd frontend
npm test
npm run build
```

From the repository root, run `python -m unittest discover -s tests -v` for the
server contract guard tests. With Playwright installed and Chrome available,
`node tests/pos-browser.mjs` from `frontend` verifies the built UI using local
fixture responses and writes screenshots to `.qa/`. These checks do not establish
a connection to a live site.

The existing `lumen_reports.dev.test_lumenpos` helper creates test users and replaces
the integration dashboard. Run it only on a disposable test site, never production.

Building locally does not install the app on the live POS site. If the POS still
shows the installation prompt from the screenshot, check that `lumen_reports`
appears in `bench --site your-pos-site list-apps` on that specific site.
