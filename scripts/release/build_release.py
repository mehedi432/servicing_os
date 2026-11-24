#!/usr/bin/env python3
"""Build a fresh-install and upgrade ZIP from a SERVICING OS Git tree."""

import argparse
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
ROOT_FILES = {
    "README.md", "pyproject.toml", "package.json", "license.txt",
    ".gitignore", ".editorconfig", ".eslintrc", ".pre-commit-config.yaml",
}
PUBLIC = "servicing_os/public/frontend/"
ENTRY_PAGE = "servicing_os/www/servicing-os.html"
FRONTEND_MANIFEST = PUBLIC + ".vite/manifest.json"
TRANSFER_FILES = ("install_servicing_os.py", "update_sources.py")


def git(*args, cwd=REPO, env=None):
    return subprocess.check_output(["git", *args], cwd=cwd, env=env)


def paths_from(data):
    return [path for path in data.decode().split("\0") if path]


def include_in_release(path):
    return path in ROOT_FILES or (
        path.startswith(("frontend/", "servicing_os/", ".github/", "scripts/release/"))
        and not any("backup" in part or ".original" in part or ".pre_rollback" in part for part in Path(path).parts)
    )


def file_at(ref, path):
    return git("show", f"{ref}:{path}")


def read_previous(path):
    if path.suffix.lower() == ".zip":
        with ZipFile(path) as archive:
            matches = [name for name in archive.namelist() if name.endswith("/counter_sources.json")]
            if len(matches) != 1:
                raise ValueError(f"Expected one source manifest in {path.name}.")
            return json.loads(archive.read(matches[0]))
    return json.loads(path.read_text(encoding="utf-8"))


def known_versions(previous):
    versions = {}
    for manifest in previous:
        for row in manifest["files"]:
            entries = versions.setdefault(row["path"], {})
            for key in (row["desired"], *row["bases"]):
                entries[key] = manifest["contents"][key]
    return versions


def source_manifest(base, tree, source_files, previous):
    older = known_versions(previous)
    base_files = set(paths_from(git("ls-tree", "-r", "--name-only", "-z", base)))
    changed = paths_from(git("diff", "--name-only", "--no-renames", "-z", base, tree))
    included = set(source_files)
    entries, contents = [], {}
    for path in sorted(changed):
        if path not in included or path.startswith(PUBLIC) or path == ENTRY_PAGE:
            continue
        desired = file_at(tree, path).decode()
        versions = dict(older.get(path, {}))
        required = path in base_files
        if required:
            original = file_at(base, path)
            versions[sha256(original).hexdigest()] = original.decode()
        fingerprint = sha256(desired.encode()).hexdigest()
        versions.pop(fingerprint, None)
        contents.update(versions)
        contents[fingerprint] = desired
        entries.append({
            "path": path, "required": required, "desired": fingerprint, "bases": sorted(versions),
        })
    return {"files": entries, "contents": contents}


def frontend_hashes(tree, paths):
    expected = set(paths)
    if not {FRONTEND_MANIFEST, ENTRY_PAGE}.issubset(expected):
        raise ValueError("Build the frontend and stage its generated files before making the release.")
    manifest = json.loads(file_at(tree, FRONTEND_MANIFEST))
    page = file_at(tree, ENTRY_PAGE).decode()
    entry = manifest["index.html"]
    for name in (entry["file"], *entry.get("css", [])):
        if f"/assets/servicing_os/frontend/{name}" not in page:
            raise ValueError(f"The rendered Frappe page does not match the frontend manifest ({name}). Rebuild the frontend.")
    for chunk in manifest.values():
        if any(PUBLIC + path not in expected for path in (chunk["file"], *chunk.get("css", []))):
            raise ValueError("A generated file in the frontend manifest is missing from the Git tree.")
    frontend = [p for p in paths if p.startswith(("frontend/", PUBLIC)) or p == ENTRY_PAGE]
    return {path: sha256(file_at(tree, path)).hexdigest() for path in frontend}


def write_standalone_repo(work, release, tree, paths, timestamp):
    snapshot = work / "snapshot"
    snapshot.mkdir()
    archive = git("archive", tree, "--", *paths)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(snapshot, filter="data")
    git("init", "-q", "-b", "release", cwd=snapshot)
    git("add", "-f", ".", cwd=snapshot)
    stamp = f"@{timestamp} +0000"
    git("-c", "user.name=SERVICING OS Release", "-c", "user.email=release@servicing.invalid",
        "commit", "-q", "--no-gpg-sign", "-m", "SERVICING OS installable source", cwd=snapshot,
        env={**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})

    bare = release / "repository/servicing_os.git"
    bare.parent.mkdir()
    git("clone", "-q", "--bare", "--no-local", str(snapshot), str(bare), cwd=work)
    git("repack", "-ad", cwd=bare)
    git("config", "--remove-section", "remote.origin", cwd=bare)
    git("fsck", "--full", cwd=bare)
    return git("rev-parse", "HEAD", cwd=bare).decode().strip()


def package_release(args):
    output = args.output.resolve()
    if output.suffix != ".zip" or not re.fullmatch(r"[A-Za-z0-9_.-]+", output.stem):
        raise ValueError("Use a ZIP file name with letters, digits, dots, dashes or underscores.")

    base = git("rev-parse", "--verify", f"{args.base}^{{commit}}").decode().strip()
    version = git("rev-parse", "--verify", f"{args.ref or 'HEAD'}^{{commit}}").decode().strip()
    tree = git("write-tree").decode().strip() if args.staged else git("rev-parse", f"{version}^{{tree}}").decode().strip()
    timestamp = int(git("show", "-s", "--format=%ct", version))
    paths = [p for p in paths_from(git("ls-tree", "-r", "--name-only", "-z", tree)) if include_in_release(p)]
    base_paths = paths_from(git("ls-tree", "-r", "--name-only", "-z", base))
    patch_paths = sorted(set(paths) | {path for path in base_paths if include_in_release(path)})
    hashes = frontend_hashes(tree, paths)
    sources = source_manifest(base, tree, paths, [read_previous(p) for p in args.previous])
    git("diff", "--check", base, tree)

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as directory:
        work = Path(directory)
        root = work / output.stem
        root.mkdir()
        for path in TRANSFER_FILES:
            (root / path).write_bytes(file_at(tree, f"scripts/release/{path}"))
        readme = file_at(tree, "scripts/release/INSTALL.md").decode().replace("RELEASE_NAME", output.stem)
        (root / "README.md").write_text(readme, encoding="utf-8")
        if args.sample:
            (root / "sample_invoice.html").write_bytes(args.sample.read_bytes())
        (root / "counter_sources.json").write_text(
            json.dumps(sources, separators=(",", ":"), ensure_ascii=False), encoding="utf-8",
        )
        (root / "frontend_hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
        (root / "servicing_os_release.patch").write_bytes(
            git("diff", "--binary", "--no-renames", base, tree, "--", *patch_paths),
        )
        standalone = write_standalone_repo(work, root, tree, paths, timestamp)
        (root / "RELEASE.txt").write_text(
            f"Git upgrade base: {base}\nSource tree: {tree}\nStandalone source commit: {standalone}\n"
            f"App files: {len(paths)}\nUpgrade source files: {len(sources['files'])}\n",
            encoding="utf-8",
        )
        archive_path = work / output.name
        with ZipFile(archive_path, "w", ZIP_DEFLATED, compresslevel=8) as archive:
            for file in sorted(root.rglob("*")):
                if not set(file.relative_to(root).parts) & {"__pycache__", "hooks"}:
                    archive.write(file, file.relative_to(work))
        with ZipFile(archive_path) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"The generated archive failed validation at {bad}.")
        archive_path.replace(output)

    print(f"{output}\nSHA-256 {sha256(output.read_bytes()).hexdigest()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Git revision used as the upgrade baseline")
    revision = parser.add_mutually_exclusive_group()
    revision.add_argument("--ref", help="Release commit or tag (default: HEAD)")
    revision.add_argument("--staged", action="store_true", help="Package the staged tree for a release candidate")
    parser.add_argument("--previous", action="append", type=Path, default=[],
                        help="Prior release ZIP or its counter_sources.json, repeat as needed")
    parser.add_argument("--sample", type=Path, help="Optional sample invoice HTML to ship in the ZIP")
    parser.add_argument("--output", type=Path, required=True, help="Path for the generated ZIP")
    try:
        package_release(parser.parse_args())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(f"Release build failed: {error}")


if __name__ == "__main__":
    main()
