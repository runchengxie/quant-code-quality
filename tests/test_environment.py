"""Environment drift checks use synthetic package metadata, never global installs."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class EnvironmentTests(unittest.TestCase):
    def run_check(self, lock, packages, *options):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "uv.lock").write_text(lock)
            for index, (name, version, direct) in enumerate(packages):
                metadata = root / f"{index}.dist-info"
                metadata.mkdir()
                (metadata / "METADATA").write_text(f"Name: {name}\nVersion: {version}\n")
                if direct is not None:
                    (metadata / "direct_url.json").write_text(json.dumps(direct))
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "research_code_quality.environment",
                    "--lock",
                    str(root / "uv.lock"),
                    "--site-packages",
                    str(root),
                    *options,
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertTrue(result.stdout, result.stderr)
            return result.returncode, json.loads(result.stdout)

    def test_version_mismatch_and_unexpected_package_fail(self):
        code, payload = self.run_check(
            'version = 1\n[[package]]\nname="demo"\nversion="2.0"\n',
            [("Demo", "1.0", None), ("extra", "1", None)],
        )
        self.assertEqual(code, 1)
        self.assertEqual(
            {item["kind"] for item in payload["drift"]}, {"version_mismatch", "unexpected_package"}
        )

    def test_unselected_extra_is_not_missing_and_names_are_normalized(self):
        code, payload = self.run_check(
            '[[package]]\nname="a-b"\nversion="1"\n[[package]]\nname="optional"\nversion="2"\n',
            [("A_B", "1", None)],
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["drift"], [])

    def test_git_commit_mismatch_fails_even_when_version_matches(self):
        code, payload = self.run_check(
            '[[package]]\nname="demo"\nversion="1"\n'
            'source={git="https://example.com/repo.git?rev=abc#abc"}\n',
            [
                (
                    "demo",
                    "1",
                    {
                        "url": "https://example.com/repo.git",
                        "vcs_info": {"commit_id": "def", "vcs": "git"},
                    },
                )
            ],
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["drift"][0]["kind"], "source_mismatch")

    def test_require_all_reports_missing(self):
        code, payload = self.run_check(
            '[[package]]\nname="demo"\nversion="1"\n', [], "--require-all"
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["drift"][0]["kind"], "missing_package")

    def test_invalid_lock_returns_json_error(self):
        code, payload = self.run_check("broken=[", [])
        self.assertEqual(code, 2)
        self.assertIn("error", payload)

    def test_duplicate_metadata_is_drift(self):
        code, payload = self.run_check(
            '[[package]]\nname="demo"\nversion="1"\n', [("demo", "1", None), ("demo", "1", None)]
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["drift"][0]["kind"], "duplicate_distribution")

    def test_matching_git_source_passes(self):
        code, _ = self.run_check(
            '[[package]]\nname="demo"\nversion="1"\n'
            'source={git="https://example.com/repo.git?rev=abc#abc"}\n',
            [
                (
                    "demo",
                    "1",
                    {
                        "url": "https://example.com/repo.git",
                        "vcs_info": {"commit_id": "abc", "vcs": "git"},
                    },
                )
            ],
        )
        self.assertEqual(code, 0)

    def test_registry_source_rejects_local_replacement(self):
        code, payload = self.run_check(
            '[[package]]\nname="demo"\nversion="1"\n', [("demo", "1", {"url": "file:///tmp/demo"})]
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["drift"][0]["kind"], "source_mismatch")

    def test_multiple_locked_versions_accept_selected_candidate(self):
        code, _ = self.run_check(
            '[[package]]\nname="demo"\nversion="1"\n[[package]]\nname="demo"\nversion="2"\n',
            [("demo", "2", None)],
        )
        self.assertEqual(code, 0)

    def test_frozen_requirements_and_target_interpreter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            freeze = root / "frozen.txt"
            freeze.write_text("demo==1\n")
            from research_code_quality.environment import read_expected

            self.assertEqual(
                read_expected(freeze, True), {"demo": [{"version": "1", "source": {}}]}
            )
            freeze.write_text("demo>=1\n")
            with self.assertRaises(ValueError):
                read_expected(freeze, True)
            freeze.write_text("demo==1\n")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "research_code_quality.environment",
                    "--requirements",
                    str(freeze),
                    "--python",
                    sys.executable,
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertIn(result.returncode, (0, 1))
            self.assertIn("checked", json.loads(result.stdout))

    def test_editable_source_uses_lock_parent(self):
        from research_code_quality.environment import source_matches

        self.assertTrue(
            source_matches(
                {"editable": "."},
                {"url": "file:///tmp/project", "dir_info": {"editable": True}},
                Path("/tmp/project"),
            )
        )
        self.assertFalse(
            source_matches(
                {"editable": "."},
                {"url": "file:///tmp/other", "dir_info": {"editable": True}},
                Path("/tmp/project"),
            )
        )

    def test_archive_source_compares_direct_url(self):
        from research_code_quality.environment import source_matches

        self.assertTrue(
            source_matches(
                {"url": "https://example.com/demo.whl"},
                {"url": "https://example.com/demo.whl"},
                Path("."),
            )
        )
        self.assertFalse(source_matches({"url": "https://example.com/demo.whl"}, None, Path(".")))

    def test_source_tree_egg_info_does_not_duplicate_installed_dist_info(self):
        from research_code_quality.environment import installed

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            egg = root / "demo.egg-info"
            egg.mkdir()
            (egg / "PKG-INFO").write_text("Name: demo\nVersion: 1\n")
            self.assertEqual(installed([str(root)]), [])

    def test_missing_metadata_directory_returns_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "uv.lock"
            lock.write_text('[[package]]\nname="demo"\nversion="1"\n')
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "research_code_quality.environment",
                    "--lock",
                    str(lock),
                    "--site-packages",
                    str(root / "missing"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("error", json.loads(result.stdout))

    def test_no_editable_contract_accepts_matching_noneditable_directory(self):
        from research_code_quality.environment import source_matches

        self.assertTrue(
            source_matches(
                {"editable": "."},
                {"url": "file:///tmp/project", "dir_info": {}},
                Path("/tmp/project"),
                no_editable=True,
            )
        )
        self.assertFalse(
            source_matches(
                {"editable": "."},
                {"url": "file:///tmp/project", "dir_info": {"editable": True}},
                Path("/tmp/project"),
                no_editable=True,
            )
        )

    def test_empty_freeze_is_invalid(self):
        from research_code_quality.environment import read_expected

        with tempfile.TemporaryDirectory() as directory:
            freeze = Path(directory) / "empty.txt"
            freeze.write_text("# no package evidence\n")
            with self.assertRaises(ValueError):
                read_expected(freeze, True)
