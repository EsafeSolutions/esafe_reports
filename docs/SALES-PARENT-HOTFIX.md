# Category sales child-table fix — 28 November 2026

The Sales screen could fail with `Field parent not found on POS Invoice Item`.
The mobile endpoint correctly filters invoice lines using the viewer's permitted
invoice names. The report engine rejected that `parent` filter because Frappe's
built-in child-table columns are not ordinary DocFields in the metadata.

`lumen_reports/report_engine.py` now recognizes `parent`, `parenttype` and
`parentfield` on child tables. Ordinary document types still reject these names
unless they are real fields. The invoice allowlist, Item visibility and the
engine's automatic `parenttype` constraint remain in the query.

## Apply

Deploy the updated reports app through the existing Frappe Cloud release workflow
for the Osaka site (the screenshot identifies `esafe-osaka.frappe.cloud`). The full
updated app is in `downloads/Esafe-BLABS-Server-Update.zip`. The small
`downloads/Esafe-BLABS-Sales-Hotfix.zip` contains the changed server module and
regression tests for applying to the existing release checkout.

Restart the Python web/workers after updating the server module, following the
site's normal deployment process. Then reopen Sales and tap **Try again**. This
fix needs no database migration, new DocField, frontend build or APK reinstall.
The workspace change is not itself a production deployment.

## Verify

The regression first reproduced the screenshot's exact failure, then passed after
the fix. It calls the real mobile endpoint, query dispatcher and report engine;
PyPika produces SQL that is executed against in-memory SQLite. Fixtures include
sales, returns, an inaccessible invoice, an inaccessible product and a different
parent document type. Both category and product sales retain only permitted POS
lines, with net amount 75 and net quantity 1.5 in the fixture.

For standalone tests, install `tests/requirements.txt` into an isolated Python
environment and run `python -m unittest discover -s tests -v`. No production data
or database is used. Actual live-site reconciliation remains a post-deployment
check.
