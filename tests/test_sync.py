import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest


MODULE = Path(__file__).resolve().parents[1] / "scripts" / "sync_skills.py"
SPEC = importlib.util.spec_from_file_location("sync_skills", MODULE)
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "collection"
        self.root.mkdir()
        self.items = [
            {"name": "alpha", "repository": "example/alpha", "ref": "main",
             "path": "skills/alpha", "license_file": "LICENSE"},
            {"name": "beta", "repository": "example/beta", "ref": "main",
             "path": ".", "license_file": "LICENSE"},
        ]
        for item in self.items:
            item["license_sha256"] = hashlib.sha256(b"MIT License\nCopyright Fixture\n").hexdigest()
        self.write_manifest()
        self.upstreams = {}
        for item in self.items:
            repo = self.base / item["name"]
            repo.mkdir()
            sync.git(repo, "init", "-q", "-b", "main")
            sync.git(repo, "config", "user.name", "Fixture")
            sync.git(repo, "config", "user.email", "fixture@example.invalid")
            directory = repo / item["path"]
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "SKILL.md").write_text(
                f"---\nname: {item['name']}\ndescription: >-\n  A test skill.\n---\n\n# Test\n"
            )
            (repo / "LICENSE").write_text("MIT License\nCopyright Fixture\n")
            self.upstreams[item["name"]] = repo
            self.commit(repo)

    def write_manifest(self):
        (self.root / "sources.json").write_text(json.dumps({"version": 1, "skills": self.items}))

    def commit(self, repo):
        sync.git(repo, "add", "-A")
        sync.git(repo, "commit", "-qm", "fixture change")

    def clone(self, item, target):
        # Real Git transport and object reads, using local upstream repositories.
        sync.git(target.parent, "clone", "--quiet", "--no-checkout", "--",
                 str(self.upstreams[item["name"]]), str(target))
        return target

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def test_complete_files_idempotence_updates_and_removals(self):
        alpha = self.upstreams["alpha"] / "skills/alpha"
        (alpha / "asset.bin").write_bytes(bytes(range(256)))
        (alpha / "run.sh").write_text("#!/bin/sh\necho fixture\n")
        (alpha / "run.sh").chmod(0o755)
        (alpha / "obsolete.txt").write_text("old")
        self.commit(self.upstreams["alpha"])
        sync.sync(self.root, clone=self.clone)
        sync.check(self.root)
        first = self.snapshot()
        sync.sync(self.root, clone=self.clone)
        self.assertEqual(first, self.snapshot())
        self.assertEqual((self.root / "skills/alpha/asset.bin").read_bytes(), bytes(range(256)))
        self.assertTrue((self.root / "skills/alpha/run.sh").stat().st_mode & 0o111)
        (alpha / "obsolete.txt").unlink()
        (alpha / "asset.bin").write_bytes(b"new")
        self.commit(self.upstreams["alpha"])
        sync.sync(self.root, clone=self.clone)
        sync.check(self.root)
        self.assertFalse((self.root / "skills/alpha/obsolete.txt").exists())
        self.assertEqual((self.root / "skills/alpha/asset.bin").read_bytes(), b"new")
        self.items.pop()
        self.write_manifest()
        sync.sync(self.root, clone=self.clone)
        sync.check(self.root)
        self.assertFalse((self.root / "skills/beta").exists())

    def test_failed_second_source_preserves_previous_snapshot(self):
        sync.sync(self.root, clone=self.clone)
        before = self.snapshot()
        alpha = self.upstreams["alpha"] / "skills/alpha/SKILL.md"
        alpha.write_text(alpha.read_text() + "new upstream text\n")
        self.commit(self.upstreams["alpha"])
        (self.upstreams["beta"] / "SKILL.md").unlink()
        self.commit(self.upstreams["beta"])
        with self.assertRaises(FileNotFoundError):
            sync.sync(self.root, clone=self.clone)
        self.assertEqual(before, self.snapshot())
        sync.check(self.root)

    def test_changed_local_file_is_detected(self):
        sync.sync(self.root, clone=self.clone)
        (self.root / "skills/alpha/SKILL.md").write_text(
            (self.root / "skills/alpha/SKILL.md").read_text() + "changed\n"
        )
        with self.assertRaisesRegex(ValueError, "content differs"):
            sync.check(self.root)

    def test_missing_license_blocks_sync(self):
        (self.upstreams["beta"] / "LICENSE").unlink()
        self.commit(self.upstreams["beta"])
        with self.assertRaisesRegex(ValueError, "license was not found"):
            sync.sync(self.root, clone=self.clone)
        self.assertFalse((self.root / "skills").exists())

    def test_symlink_blocks_sync(self):
        (self.upstreams["beta"] / "escape").symlink_to("/etc/passwd")
        self.commit(self.upstreams["beta"])
        with self.assertRaisesRegex(ValueError, "unsupported symlink"):
            sync.sync(self.root, clone=self.clone)
        self.assertFalse((self.root / "skills").exists())

    def test_changed_license_requires_review_and_preserves_snapshot(self):
        sync.sync(self.root, clone=self.clone)
        before = self.snapshot()
        (self.upstreams["beta"] / "LICENSE").write_text("Changed terms\n")
        self.commit(self.upstreams["beta"])
        with self.assertRaisesRegex(ValueError, "license changed"):
            sync.sync(self.root, clone=self.clone)
        self.assertEqual(before, self.snapshot())

    def test_unsafe_manifest_paths_are_rejected(self):
        for path in ("../outside", "/absolute", ".git/config", "a\\b"):
            with self.subTest(path=path):
                self.items[0]["path"] = path
                self.write_manifest()
                with self.assertRaises(ValueError):
                    sync.load_sources(self.root)


if __name__ == "__main__":
    unittest.main()
