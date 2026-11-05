#!/usr/bin/env python3
"""Mirror selected public GitHub skill directories without running upstream code."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile


def git(directory, *args, binary=False):
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(directory), *args],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, timeout=180,
    )
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def safe_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"Invalid relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or any(
        part.lower() == ".git" for part in path.parts
    ):
        raise ValueError(f"Unsafe relative path: {value!r}")
    return path


def load_sources(root):
    data = json.loads((root / "sources.json").read_text())
    if data.get("version") != 1 or not data.get("skills"):
        raise ValueError("Expected sources.json version 1 with at least one skill")
    names = set()
    for item in data["skills"]:
        name = item["name"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or name in names:
            raise ValueError(f"Invalid or duplicate skill name: {name}")
        names.add(name)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", item["repository"]):
            raise ValueError("Expected a GitHub owner/repository")
        if not isinstance(item["ref"], str) or not item["ref"] or item["ref"].startswith("-"):
            raise ValueError("Expected a branch or tag")
        safe_path(item["path"])
        safe_path(item["license_file"])
        if not re.fullmatch(r"[0-9a-f]{64}", item.get("license_sha256", "")):
            raise ValueError("Expected the reviewed license SHA-256")
    return data["skills"]


def clone_upstream(item, target):
    git(target.parent, "clone", "--quiet", "--depth", "1", "--single-branch",
        "--no-checkout", "--branch", item["ref"], "--",
        f"https://github.com/{item['repository']}.git", str(target))
    return target


def validate_skill(directory, expected_name):
    text = (directory / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError(f"{expected_name}: missing SKILL.md frontmatter")
    end = lines.index("---", 1)
    front = "\n".join(lines[1:end])
    name = re.search(r"^name:\s*['\"]?([a-z0-9-]+)['\"]?\s*$", front, re.M)
    description = re.search(r"^description:\s*\S", front, re.M)
    if not name or name.group(1) != expected_name or not description:
        raise ValueError(f"{expected_name}: missing or mismatched name/description")
    if not (directory / "LICENSE").is_file():
        raise ValueError(f"{expected_name}: missing upstream LICENSE")
    nested = [p for p in directory.rglob("SKILL.md") if p != directory / "SKILL.md"]
    if nested:
        raise ValueError(f"{expected_name}: choose a single skill directory, found {nested}")


def fingerprint(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not supported: {path}")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "executable": bool(path.stat().st_mode & 0o111),
            }
    return result


def export_skill(item, checkout, output):
    revision = git(checkout, "rev-parse", "HEAD")
    prefix = "" if item["path"] == "." else safe_path(item["path"]).as_posix() + "/"
    entries = git(checkout, "ls-tree", "-rz", "HEAD", binary=True).split(b"\0")
    output.mkdir(parents=True)
    license_found = False
    for raw in filter(None, entries):
        header, path_bytes = raw.split(b"\t", 1)
        mode, kind, sha = header.decode().split()
        path = path_bytes.decode("utf-8")
        safe_path(path)
        is_license = path == item["license_file"]
        if not path.startswith(prefix) and not is_license:
            continue
        if kind != "blob" or mode not in ("100644", "100755"):
            raise ValueError(f"{item['name']}: unsupported symlink/submodule {path}")
        relative = "LICENSE" if is_license else path[len(prefix):]
        destination = output.joinpath(*safe_path(relative).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(git(checkout, "cat-file", "blob", sha, binary=True))
        destination.chmod(0o755 if mode == "100755" else 0o644)
        license_found |= is_license
    if not license_found:
        raise ValueError(f"{item['name']}: upstream license was not found")
    validate_license(item, output)
    validate_skill(output, item["name"])
    return {
        "repository": item["repository"], "ref": item["ref"],
        "path": item["path"], "revision": revision,
        "files": fingerprint(output),
    }


def validate_license(item, directory):
    digest = hashlib.sha256((directory / "LICENSE").read_bytes()).hexdigest()
    if digest != item["license_sha256"]:
        raise ValueError(f"{item['name']}: license changed; review before redistributing")


def sync(root, clone=clone_upstream):
    items = load_sources(root)
    # Finish all downloads and checks before replacing any installed snapshots.
    with tempfile.TemporaryDirectory(prefix="skill-sync-") as temporary:
        temp = Path(temporary)
        staged = temp / "skills"
        lock = {"version": 1, "skills": {}}
        for item in items:
            checkout = clone(item, temp / (item["name"] + "-upstream"))
            lock["skills"][item["name"]] = export_skill(
                item, checkout, staged / item["name"]
            )
            print(f"Synced {item['name']} at {lock['skills'][item['name']]['revision'][:12]}")
        target = root / "skills"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(staged, target, copy_function=shutil.copy2)
        (root / "sources.lock.json").write_text(
            json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def check(root):
    items = load_sources(root)
    lock = json.loads((root / "sources.lock.json").read_text())
    if set(lock["skills"]) != {item["name"] for item in items}:
        raise ValueError("Source manifest and lock file disagree")
    expected_dirs = {item["name"] for item in items}
    if {p.name for p in (root / "skills").iterdir()} != expected_dirs:
        raise ValueError("Unexpected or missing skill directory")
    for item in items:
        directory = root / "skills" / item["name"]
        validate_skill(directory, item["name"])
        validate_license(item, directory)
        record = lock["skills"][item["name"]]
        if any(record[k] != item[k] for k in ("repository", "ref", "path")):
            raise ValueError(f"{item['name']}: lock source mismatch")
        if not re.fullmatch(r"[0-9a-f]{40}", record["revision"]):
            raise ValueError("Invalid upstream revision")
        if fingerprint(directory) != record["files"]:
            raise ValueError(f"{item['name']}: content differs from lock file")
    print(f"Validated {len(items)} installable skills and all file hashes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate without accessing the network")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        (check if args.check else sync)(args.root.resolve())
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Skill sync failed: {error}\n")
