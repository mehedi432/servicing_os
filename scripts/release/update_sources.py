#!/usr/bin/env python3
"""Safely apply the cumulative SERVICING OS source update."""

import argparse
import ast
from dataclasses import dataclass
from difflib import SequenceMatcher
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile


SOURCE_FILE = Path(__file__).with_name("counter_sources.json")
CONFLICT = re.compile(
    rb"^<{17} LOCAL\n(.*?)^\|{17} BASE\n(.*?)^={17}\n(.*?)^>{17} GRID\n",
    re.MULTILINE | re.DOTALL,
)


@dataclass(frozen=True)
class Change:
    path: Path
    before: bytes | None
    after: bytes
    release_sha256: str
    note: str = ""


def fingerprint(content):
    return sha256(content).hexdigest()


def merge_disjoint_line(conflict):
    local, base, release = conflict.groups()
    if any(len(value) > 2500 or value.count(b"\n") != 1 for value in (local, base, release)):
        return conflict.group()
    edits = set()
    for text in (local, release):
        for op, start, end, first, last in SequenceMatcher(None, base, text, autojunk=False).get_opcodes():
            if op != "equal":
                edits.add((start, end, text[first:last]))
    merged, position, previous_start = [], 0, -1
    for start, end, text in sorted(edits):
        if start < position or start == previous_start:
            return conflict.group()
        merged.extend((base[position:start], text))
        position, previous_start = end, start
    return b"".join([*merged, base[position:]])


def merge_file(current, base, desired, temporary):
    ours, ancestor, theirs = (temporary / name for name in ("local", "base", "release"))
    for path, value in ((ours, current), (ancestor, base), (theirs, desired)):
        path.write_bytes(value)
    result = subprocess.run(
        ["git", "merge-file", "-p", "--diff3", "--marker-size=17",
         "-L", "LOCAL", "-L", "BASE", "-L", "GRID", str(ours), str(ancestor), str(theirs)],
        capture_output=True,
    )
    if result.stderr and result.returncode:
        raise ValueError("Git could not merge the source: " + result.stderr.decode(errors="replace").strip())
    if result.returncode == 0:
        return result.stdout
    if 0 < result.returncode < 128 and CONFLICT.search(result.stdout):
        resolved = CONFLICT.sub(merge_disjoint_line, result.stdout)
        if CONFLICT.search(resolved) is None:
            return resolved
    return None


def merge(current, bases, desired, temporary, relative):
    suffix = Path(relative).suffix
    if suffix == ".vue":
        for base in sorted(bases, key=len, reverse=True):
            if current.startswith(base):
                tail = current[len(base):]
                if re.fullmatch(rb"(?:\s*<style\b[^>]*>.*?</style>)+\s*", tail, re.DOTALL):
                    return desired + tail, "Preserved appended styles"

    current_lines = current.decode("utf-8").splitlines(keepends=True)
    ranked = [(SequenceMatcher(None, base.decode("utf-8").splitlines(keepends=True), current_lines,
                               autojunk=False).ratio(), base)
              for base in bases]
    best = max(score for score, _ in ranked)
    if best < 0.80:
        raise ValueError("source differs substantially from the packaged versions")

    closest = [base for score, base in ranked if score == best]
    results = {merge_file(current, base, desired, temporary) for base in closest}
    if len(results) == 1 and None not in results:
        return results.pop(), "Merged local changes"
    raise ValueError("local edits overlap the current release")


def validate_vue(app, relative, content, temporary):
    candidate = temporary / Path(relative).name
    candidate.write_bytes(content)
    validator = r"""
const fs = require('node:fs')
const { parse, compileScript } = require('@vue/compiler-sfc')
const source = fs.readFileSync(process.argv[1], 'utf8')
const { descriptor, errors } = parse(source, { filename: process.argv[1] })
if (errors.length) throw new Error(errors.map(error => error.message || error).join('\n'))
compileScript(descriptor, { id: 'servicing-os-preflight', inlineTemplate: true })
"""
    result = subprocess.run(["node", "-e", validator, os.fspath(candidate)],
                            cwd=app / "frontend", stdin=subprocess.DEVNULL, capture_output=True)
    if result.returncode:
        error = result.stderr.decode(errors="replace")
        message = next((line for line in error.splitlines() if "Error:" in line), "Vue validation failed")
        raise ValueError(message + ". Ensure frontend dependencies are installed or review the local Vue source.")


def read_source(app, path):
    if path.is_symlink() or path.resolve() != app / path.relative_to(app):
        raise ValueError("source uses a symbolic link")
    return path.read_bytes() if path.exists() else None


def backup_root(app):
    return app.parent.parent / ".servicing_os_patch_backups" / "source-updates"


def installed_versions(app):
    versions = set()
    for path in backup_root(app).glob("*/manifest.json"):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if manifest["app"] == str(app):
                for entry in manifest["files"]:
                    versions.add((entry["path"], entry["release_sha256"], entry["installed_sha256"]))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return versions


def plan(app, sources):
    contents = {key: value.encode("utf-8") for key, value in sources["contents"].items()}
    recorded = installed_versions(app)
    changes, blocked = [], []
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        for item in sources["files"]:
            relative = item["path"]
            path = app / relative
            try:
                current = read_source(app, path)
                desired = contents[item["desired"]]
                note = ""
                if current == desired:
                    continue
                if current is not None and (relative, item["desired"], fingerprint(current)) in recorded:
                    continue
                bases = [contents[key] for key in item["bases"]]
                if current is None and item["required"]:
                    raise ValueError("existing source file is missing")
                if (current is not None and path.suffix == ".vue" and current.startswith(desired)
                        and re.fullmatch(rb"(?:\s*<style\b[^>]*>.*?</style>)+\s*", current[len(desired):], re.DOTALL)):
                    continue
                if current is not None and not bases:
                    raise ValueError("a local file already uses this new release path")
                if current is not None and current not in bases:
                    desired, note = merge(current, bases, desired, temporary, relative)
                if path.suffix == ".py":
                    ast.parse(desired, filename=relative)
                elif path.suffix == ".json":
                    json.loads(desired)
                if current != desired:
                    if path.suffix == ".vue" and note:
                        validate_vue(app, relative, desired, temporary)
                    changes.append(Change(path, current, desired, item["desired"], note))
            except (OSError, SyntaxError, ValueError) as error:
                blocked.append((relative, str(error)))
    return changes, blocked


def atomic_write(path, content, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".counter-", dir=path.parent)
    staged = Path(name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        staged.chmod(mode)
        staged.replace(path)
    finally:
        staged.unlink(missing_ok=True)


def apply(app, changes):
    parent = backup_root(app)
    parent.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(dir=parent))
    manifest = []
    for change in changes:
        relative = change.path.relative_to(app)
        mode = stat.S_IMODE(change.path.stat().st_mode) if change.before is not None else 0o644
        if change.before is not None:
            atomic_write(backup / "original" / relative, change.before, mode)
        manifest.append({"path": relative.as_posix(), "created": change.before is None, "release_sha256": change.release_sha256,
                         "installed_sha256": fingerprint(change.after), "mode": mode})
    (backup / "manifest.json").write_text(json.dumps({"app": str(app), "files": manifest}, indent=2), encoding="utf-8")
    print(f"Source backup: {backup}", flush=True)

    written = []
    try:
        for change, item in zip(changes, manifest):
            if read_source(app, change.path) != change.before:
                raise ValueError(f"Source changed during the update: {item['path']}")
            atomic_write(change.path, change.after, item["mode"])
            written.append((change, item))
    except (OSError, ValueError, KeyboardInterrupt):
        for change, item in reversed(written):
            if read_source(app, change.path) != change.after:
                print(f"Check this concurrently edited file against the backup: {item['path']}", file=sys.stderr)
            elif change.before is None:
                change.path.unlink()
            else:
                atomic_write(change.path, change.before, item["mode"])
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "apply"))
    parser.add_argument("--app", type=Path, default=Path("apps/servicing_os"))
    args = parser.parse_args()
    app = args.app.resolve()
    if not (app / "frontend/package.json").is_file() or not (app / "servicing_os/hooks.py").is_file():
        raise ValueError("Run from the Bench folder, or pass --app with the SERVICING OS app directory.")

    sources = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    changes, blocked = plan(app, sources)
    if blocked:
        for relative, error in blocked:
            print(f"BLOCKED {relative} · {error}", file=sys.stderr)
        return 1
    if not changes:
        print("SERVICING OS sources are already up to date.")
        return 0
    for change in changes:
        note = f" · {change.note}" if change.note else ""
        print(f"UPDATE {change.path.relative_to(app)}{note}")
    if args.action == "apply":
        apply(app, changes)
        print("SERVICING OS sources updated. Migrate, rebuild the frontend and restart Bench.")
    else:
        print(f"Check passed for {len(changes)} source files.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        sys.exit(f"STOP {error}")
