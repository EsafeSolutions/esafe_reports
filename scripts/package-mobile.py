"""Package explicit app source paths, excluding caches, credentials and build tools."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "downloads"
OUT.mkdir(exist_ok=True)


def source_files(paths):
    for relative in paths:
        path = ROOT / relative
        for item in sorted(path.rglob("*") if path.is_dir() else [path]):
            if not item.is_file() or item.is_symlink():
                continue
            if any(part in {"node_modules", "__pycache__", ".git", ".qa"} for part in item.parts):
                continue
            if item.suffix in {".pyc", ".map", ".jks", ".keystore", ".idsig"} or item.name.startswith(".env"):
                continue
            yield item


def package(name, paths):
    with zipfile.ZipFile(OUT / name, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in source_files(paths):
            archive.write(item, "esafe_reports/" + item.relative_to(ROOT).as_posix())


package("Esafe-BLABS-Mobile-Source.zip", ["native", "scripts/prepare-android.ps1", "scripts/build-android.ps1", "license.txt", "TRADEMARKS.md"])
package("Esafe-BLABS-Server-Update.zip", ["lumen_reports", "frontend/src", "frontend/tests", "frontend/package.json", "frontend/yarn.lock", "frontend/index.html", "frontend/vite.config.js", "frontend/postcss.config.js", "frontend/tailwind.config.js", "tests", "docs", "native", "scripts", "package.json", "pyproject.toml", "README.md", "license.txt", "TRADEMARKS.md"])
package("Esafe-BLABS-Sales-Hotfix.zip", ["lumen_reports/report_engine.py", "tests/test_report_engine_child_fields.py", "tests/requirements.txt", "docs/SALES-PARENT-HOTFIX.md", "license.txt"])

guide = """ESAFE BLABS — Osaka mobile app

Android: transfer Esafe-BLABS-Android-development.apk to the phone and tap to install.
This APK is development-signed; it is not a Play Store release.

iPhone: open https://osaka.cloud.esafe.lk/esafe-report/mobile?tab=products in Safari.
Tap Share > Add to Home Screen > Add, then open the ESAFE icon.

Sign in with your existing Osaka account. Internet access is needed for live data.

DEPLOY THE SERVER UPDATE FIRST to activate the new Products, Inventory and Sales
screens. Installing an APK or Home Screen icon does not update the Osaka server.
The server has not been deployed from this workspace.

Esafe-BLABS-Server-Update.zip: the complete reports-app release source and built assets.
Esafe-BLABS-Mobile-Source.zip: native source and build scripts (optional native iOS source included).
Esafe-BLABS-Sales-Hotfix.zip: server fix for 'Field parent not found on POS Invoice Item'.
See esafe_reports/docs/SALES-PARENT-HOTFIX.md inside the hotfix ZIP. No APK reinstall is needed.

Deployment and permissions: esafe_reports/native/README.md inside either ZIP.
No site backup, credentials, private signing keys or real business data are included.
"""
(OUT / "INSTALL.txt").write_text(guide, encoding="utf-8")
files = [OUT / "Esafe-BLABS-Android-development.apk", OUT / "Esafe-BLABS-Mobile-Source.zip", OUT / "Esafe-BLABS-Server-Update.zip", OUT / "Esafe-BLABS-Sales-Hotfix.zip"]
(OUT / "SHA256SUMS.txt").write_text("\n".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in files) + "\n", encoding="ascii")
for path in files:
    print(f"{path.name}: {path.stat().st_size:,} bytes")
