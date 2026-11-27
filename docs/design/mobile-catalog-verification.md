# Mobile catalogue verification — 27 November 2026

Concept: [mobile-catalog-concept.png](mobile-catalog-concept.png).
Design tokens and intentional functional additions are recorded in
[mobile-catalog-design.md](mobile-catalog-design.md).
Final captures: [Products](mobile-catalog-products.png),
[Inventory](mobile-catalog-inventory.png), [Sales](mobile-catalog-sales.png).
The combined preview is [mobile-catalog-preview.png](mobile-catalog-preview.png).

## Method

Browser/IAB was attempted first against the Windows loopback preview; it returned
`ERR_CONNECTION_TIMED_OUT`. Local Chrome through the bundled Playwright runtime
was used as the fallback. All browser checks serve the actual production Vite
bundle with the explicitly named `mobile-fixture.mjs`. No production records or
credentials enter the fixtures, concept, screenshots or downloadable packages.

The concept is a 1536×1024 board containing three separate phone screens, rather
than a single application viewport. Its screen composition is compared with
individual 390×844 native browser-pixel captures. The browser flow additionally
checks 320×740 and 1440×1000. The concept and latest captures are opened using
`view_image` in the final QA pass.

## Comparison ledger

| Point | Concept / final check | Outcome |
| --- | --- | --- |
| Shell | Brand/header, five fixed tabs, teal selected state, navy outline icons | Same hierarchy and icon treatment; repository B-star replaces the illustrative B |
| Products | Search, category/price-list selects, separated rows, prices and stock | Retained; explicit per-UOM labels and price-list notice avoid ambiguous prices |
| Inventory | Warehouse/category selectors, pale teal summary, stock segments and rows | Retained; summary counts products on this page rather than adding incompatible units |
| Sales | Date/outlet controls, navy summary, ranked teal bars, product entry point | Retained; summary counts categories/products rather than mixed physical quantities |
| Typography | Jakarta Sans, bold navy headings, quiet metadata, aligned numbers | Bundled font, deliberate heading/row/control sizes; phone text remains readable |
| Palette | White surfaces, #11264a text, #008f83 actions, #e4f5f3 selections | Matched; no photographs or generated bitmap controls |
| Spacing | Open lists, hairline dividers, bounded controls, bottom navigation | Matched; removed the extra date line on Sales and tightened ranking rows to expose the product action |
| Interaction states | Search focus, selected filters, details, pagination, exports | Working controls; screenshots clear transient hover/focus decoration |
| Responsive | Complete phone screens with scrolling for real data | No horizontal overflow at 320/390/1440; English and Arabic, light and dark checked |

Above-the-fold copy was compared against the concept's brand, screen titles,
search labels, selects, stock segments and navigation. Intentional differences:
actual values and page sizes replace illustrative data; the catalogue explains
price-list rates/UOM; stock totals explicitly cover permitted warehouses; sales
notes submitted POS net amounts, returns and tax treatment; summaries do not add
mixed UOMs. Product details, pagination, CSV export, retry/offline/permission and
partial-result notices are functional additions. Settings adds the explicitly
requested Android APK download. No extra marketing copy or decorative panels
were introduced.

The implementation is faithfully verified against the concept's visual system,
including layout, palette, typography, icons, list anatomy and responsive behavior.
The listed functional/data differences are intentional. No unresolved material
visual mismatch was found in this comparison.

## Functional checks

- Production frontend build succeeded. Existing bundled-font URL and large chart
  chunk warnings remain; catalogue screens do not load the chart library.
- 49 Python tests: 47 passed, two existing optional transport/runtime tests skipped
  because this standalone environment lacks pywebpush/Werkzeug. New tests cover
  reporting roles, field-level price/stock permissions, visible warehouse filtering,
  current price validity, permission-scoped invoice/Item aggregation, currency
  isolation, input validation and partial-result disclosure.
- 13 Node tests passed, including unknown stock, explicit UOM price selection and
  CSV formula protection.
- Catalogue Chrome flow passed search/exact barcode, price lists, item detail,
  pagination, category/warehouse filters, stock filters, date/outlet sales, category
  drill-down, CSV download/native bridge, APK asset, partial results, offline recovery,
  permission loss, Arabic/dark appearance and 320/390/1440 layouts. CSV uses one BOM.
- Existing mobile Chrome flow passed Overview/Reports/Alerts, installation guidance,
  filters, setup, permission revocation, simulated push and service-worker privacy.
- Existing POS Chrome suite passed routes, setup, permissions and deployment refresh.
- Android APK compiled and verified with Android `apksigner`; v2/v3 signatures are
  valid. Manifest inspection confirms package `lk.esafe.blabs`, min API 24, target
  API 36 and only the Internet permission. Public and local APK files match.
- The Osaka URL returned HTTP 200 after redirecting to the existing Frappe login.

## Practical limits

No live deployment, authenticated ERPNext reconciliation, Android-device install,
iPhone Home Screen install or OS share-sheet test was performed. Those checks need
the released server and actual devices. The user selected iPhone Home Screen
distribution, so a signed native IPA/TestFlight release is not part of this handoff.
The optional iOS native source is included but cannot be built on Windows.

Installable downloads are development artifacts. The server release must be deployed
to enable the new UI and endpoints; installing an APK/Home Screen icon does not
update the server. Native-source and server-update archives exclude private keys,
node_modules, toolchains, caches, environment files and site/database backups.
