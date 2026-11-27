# ESAFE prices, stock and sales app

Configured site: **https://osaka.cloud.esafe.lk**. Sign in using the site's existing
Frappe account. No passwords, API keys, customer data or signing secrets are bundled.

## Downloads and installation

- `downloads/Esafe-BLABS-Android-development.apk`: an installable Android 7.0+
  APK, compiled against Android 16/API 36 and signed with a development certificate.
  Copy/download it to the phone, tap it and follow Android's installation prompts.
  It is not a Play Store release. Keep the development keystore in `.qa/android-signing/`
  if you need compatible updates to this development build. For public distribution,
  rebuild using the organization's release key; changing certificates requires
  uninstalling the development app first.
  After deployment, web Settings also includes **Download Android APK**, served
  from `/assets/lumen_reports/downloads/Esafe-BLABS-Android-development.apk`.
- **iPhone:** open `https://osaka.cloud.esafe.lk/esafe-report/mobile?tab=products`
  in Safari, tap Share → Add to Home Screen → Add. Open the ESAFE icon to use the
  full screen app. This is the selected iPhone distribution method; no Apple
  Developer account is required. Prices, stock and reports require internet access.
- `downloads/Esafe-BLABS-Mobile-Source.zip`: Android/iOS source and build scripts.
- `downloads/Esafe-BLABS-Server-Update.zip`: complete report-app source and built
  web assets for the existing Frappe installation. Contains no database/site backup.

**Deploy the server update before expecting the new product/inventory screens on
either device.** The native Android app loads the site's authenticated mobile app;
installing its APK does not deploy the server. The Osaka URL was checked and redirects
to the normal login page. No production deployment or real business-data test was
performed from this workspace.

## Features

- Products: search name/code/exact barcode, category selection and selling price
  lists. Rates show their selling UOM; product details list current rates, validity
  selection, and packing units. Customer/batch-specific rates, pricing rules and
  checkout tax calculations are outside this price-list enquiry.
- Inventory: actual stock in permitted warehouses, warehouse/category/search
  selection, per-product warehouse details, reserved/ordered/projected quantities,
  zero/negative stock states and CSV export. Each quantity retains its stock UOM.
  The In stock/Out of stock controls explicitly filter the current product page.
- Sales: date/outlet filters, category ranking, category-to-product drill-down,
  signed quantities including returns, product view and CSV export. Amounts are
  submitted POS line `base_net_amount` (net of returns, excluding tax). Current
  Item categories are used. Consolidated Sales Invoices are not counted again.
  Different company base currencies are never added together; select one outlet
  if the site's companies use different currencies.
- Existing Overview, Reports, Alerts, settings, English/Arabic and dark appearance
  remain available. Reports is reached from Overview; Alerts uses the header bell.
- Android includes native Home/Refresh, back navigation, connection recovery and
  the OS share sheet for CSV. iPhone Home Screen uses browser CSV download/share.
  Native Android WebView push is not supported; existing web-push functionality
  remains available in supported installed browser apps.

## Server deployment

Use the existing ESAFE reports release process to deploy this checkout, including
`lumen_reports/mobile_catalog.py`, the updated web assets, and the rest of the app.
The server ZIP contains a complete `esafe_reports/` source directory. Review it in
an isolated release checkout; do not overwrite site configuration or databases.

From the bench, after the release checkout has been updated:

```sh
bench setup requirements --python
bench build --app lumen_reports
bench --site osaka.cloud.esafe.lk migrate
bench --site osaka.cloud.esafe.lk clear-cache
bench restart
```

Frappe Cloud uses the normal app/bench deployment workflow. This workspace has no
authenticated Frappe Cloud deployment session. The frontend build is included for
sites that cannot rebuild locally, following this repository's existing convention.
No new DocTypes or automatically granted permissions are introduced by the catalogue.

Assign the normal reporting role, the POS dashboard audience and the relevant read
permissions for Item, Item Group, Item Price, Price List, Bin, Warehouse, Company,
POS Invoice and its item fields. The app checks role, field and row permissions.
Missing price/stock access shows an unavailable state, never an invented zero.
Restricted Viewers still need access to the POS dashboard for sales.

Check after deployment:

1. Log in as an actual reporting user on both phones.
2. Products: match an exact barcode, price list and UOM against Item Price.
3. Inventory: compare a product's warehouse actual/reserved/ordered/projected values
   with ERPNext. A missing accessible Bin represents zero; inaccessible stock is
   not represented as zero. Stock totals cover only visible warehouses.
4. Sales: choose a known period/outlet and reconcile net line amounts and returns
   against submitted POS Invoices. Check a user with restricted invoice/Item access.
5. Install the APK and iPhone Home Screen app, reopen, sign in, export/share a CSV,
   check offline retry and return online. Native OS/device behavior requires devices.

Limits are explicit: 20 products per page; up to 200 option choices; 500 price rows
and 1,000 Bin rows per page; sales scope up to 20,000 visible invoices/items with
up to 500 aggregate groups per batch. Capped results show a partial-result warning.
Choose a smaller date range, category, warehouse or product to get complete detail.
Authenticated responses are not cached by the service worker; CSVs are exported
only after a user action. Native share exports stay in the app's private cache.

## Build Android

The native app uses Android framework APIs, with no third-party runtime libraries.
From the project root on Windows:

```powershell
.\scripts\prepare-android.ps1
.\scripts\build-android.ps1
```

Preparation downloads Eclipse Temurin 17 (SHA256 checked) and the official Google
Android API 36 platform/build tools into the ignored `.qa/android-tools/` directory.
Build compiles resources and Java, desugars bytecode, aligns the APK and signs it.
It then runs `apksigner verify` and inspects the manifest using `aapt dump badging`.
Custom signing uses `-Keystore` and `-Alias`; set `ESAFE_APK_STORE_PASS` and
`ESAFE_APK_KEY_PASS` locally, never in source or command arguments.

## Optional future iOS native distribution

The source also contains `ios/EsafeBLABS.xcodeproj`, a SwiftUI/WKWebView app with
the same HTTPS site, persistent first-party sign-in, native retry/home and CSV share.
Open on a Mac with Xcode, select the ESAFE Apple Developer team under Signing &
Capabilities, choose a device, and build/archive. A signed IPA/TestFlight build
requires the appropriate Apple account and provisioning. No iOS build, signing or
native iOS device test was possible on this Windows machine. The user's selected
iPhone Home Screen app does not depend on this optional native project.

## Verification

The production frontend, Python permission/scoping tests, Node helper tests and
Chrome browser flows are checked locally. Browser tests use isolated fixtures,
not live sales or stock. See `docs/design/mobile-catalog-verification.md` for
screen comparisons, viewport checks, test results and remaining device/server checks.
