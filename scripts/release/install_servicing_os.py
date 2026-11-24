#!/usr/bin/env python3
"""Prepare SERVICING OS on a fresh or existing Frappe/ERPNext v15 site."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def run(*command, cwd=None, capture=False):
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=capture).stdout


def packaged_frontend_matches(app):
    from hashlib import sha256
    expected = json.loads((ROOT / "frontend_hashes.json").read_text())
    return all((app / path).is_file() and sha256((app / path).read_bytes()).hexdigest() == checksum
               for path, checksum in expected.items())


def require(*commands):
    missing = [command for command in commands if not shutil.which(command)]
    if missing:
        raise ValueError("Required on this Bench host: " + ", ".join(missing))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, help="Existing ERPNext v15 site name")
    parser.add_argument("--company", help="Exact ERPNext Company name for a multi-company site")
    parser.add_argument("--check", action="store_true", help="Check site versions and source compatibility")
    parser.add_argument("--restart", action="store_true", help="Restart a production Bench after verification")
    args = parser.parse_args()
    bench = Path.cwd()
    app = bench / "apps/servicing_os"
    if not (bench / "apps/frappe").is_dir() or not (bench / "sites" / args.site / "site_config.json").is_file():
        raise ValueError("Run from the Bench root and use an existing site name.")
    require("bench", "git")
    site = ("bench", "--site", args.site)
    output = run(*site, "list-apps", "--format", "text", capture=True)
    apps = {fields[0]: fields[1] for line in output.splitlines() if len(fields := line.split()) >= 2}
    if any(not apps.get(name, "").startswith("15.") for name in ("frappe", "erpnext")):
        raise ValueError("This release needs Frappe and ERPNext v15 installed on the selected site.")
    if "servicing_os" in apps and not app.is_dir():
        raise ValueError("This site already uses SERVICING OS but its app folder is missing. Restore the app source before upgrading.")

    rebuild = app.is_dir() and not packaged_frontend_matches(app)
    if app.is_dir():
        if rebuild:
            require("node", "npm")
        if not args.check and rebuild and not (app / "frontend/node_modules/@vue/compiler-sfc").is_dir():
            run("npm", "install", "--no-save", "--package-lock=false", "--no-audit", "--no-fund",
                cwd=app / "frontend")
        run(sys.executable, str(ROOT / "update_sources.py"), "check")
    if args.check:
        print(f"Preflight passed for {args.site}. {'Upgrade' if app.is_dir() else 'Fresh app install'}.")
        return

    run(*site, "backup", "--with-files")
    if not app.is_dir():
        repository = ROOT / "repository/servicing_os.git"
        if not (repository / "HEAD").is_file():
            raise ValueError("Extract the complete ZIP, including its repository folder.")
        run("bench", "get-app", "servicing_os", str(repository), "--branch", "release", "--skip-assets")
    else:
        run(sys.executable, str(ROOT / "update_sources.py"), "apply")
        if rebuild:
            run("npm", "ci", "--no-audit", "--no-fund", cwd=app / "frontend")
            run("npm", "run", "build", cwd=app / "frontend")

    if "servicing_os" not in apps:
        run(*site, "install-app", "servicing_os")
    run(*site, "migrate")
    kwargs = ("--kwargs", json.dumps({"company": args.company})) if args.company else ()
    run(*site, "execute", "servicing_os.site_setup.prepare", *kwargs)
    if args.company:
        run(*site, "set-config", "servicing_os_company", args.company)
    run(*site, "execute", "servicing_os.deployment.verify")
    manifest_path = app / "servicing_os/public/frontend/.vite/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    files = [filename for entry in manifest.values() for filename in [entry["file"], *entry.get("css", [])]]
    if not all((bench / "sites/assets/servicing_os/frontend" / file).is_file() for file in files):
        run("bench", "build", "--app", "servicing_os")
    if not all((bench / "sites/assets/servicing_os/frontend" / file).is_file() for file in files):
        raise ValueError("The release is installed, but Bench is not serving the SERVICING OS asset files.")
    run(*site, "clear-cache")
    if args.restart:
        run("bench", "restart")
    print(f"Verified {args.site}. Open /servicing-os and refresh the browser.")
    if not args.restart:
        print("If Bench is already running, restart its web and worker processes before opening the app.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.strip(), file=sys.stderr)
        sys.exit(f"Installation paused: {error}")
