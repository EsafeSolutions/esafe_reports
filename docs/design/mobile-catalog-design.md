# Catalogue design specification

Reference: `mobile-catalog-concept.png` (1536 × 1024, three complete phone screens).
Extends the existing mobile app, keeping its header, brand asset and mobile shell.

- White surface, navy #11264a type, teal #008f83 actions, pale teal #e4f5f3 selected states.
- Bundled Plus Jakarta Sans; heading 29px/800, row title 16px/750, body/control 14px, metadata 11–12px.
- Five fixed navigation items: Overview, Products, Sales, Inventory, Settings. Alerts remain in the header; Reports remain under Overview.
- Products: heading/refresh, search, category and price list selects, rate note, separated product rows, pagination, export. Product details use the existing dialog component family.
- Inventory: same search/filter controls, warehouse select, page summary, stock segment control, separated product rows.
- Sales: shared date/outlet controls, navy summary, ranked teal bars, category drill-down, product view and CSV export.
- Outline icons match the existing 1.7px SVG family. No photography, bitmap controls, gradients or added decorative elements.

Intentional differences required by real data: quantities are shown with individual stock units rather than summing incompatible units; the sales summary counts categories/products rather than summing mixed units. Rates are explicitly price-list rates, not checkout totals. All datasets are permission-scoped. Pagination, export, retry, empty, offline and permission states complete the workflows. No concept values enter production.
