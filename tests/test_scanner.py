import io
import json
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from research_code_quality.scanner import (
    DEFAULT_ROOTS,
    discover_python_files,
    main,
    parse_args,
    ratchet_violations,
    scan_repository,
    write_baseline,
)


class ScannerScopeTests(unittest.TestCase):
    def test_nested_git_scopes_include_source_and_preserve_directory_boundaries(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            files = {
                "src/runtime/worker.py": "def large():\n" + "    pass\n" * 101,
                "src/runtime/new.py": "pass\n",
                "src/runtime_extra/other.py": "pass\n",
                "src/other/other.py": "pass\n",
                "scripts/dev/audit.py": "pass\n",
                "tests/test_worker.py": "pass\n",
                "src/runtime/ignored.py": "pass\n",
            }
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            (root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", "src/runtime/worker.py"], check=True
            )
            expected = sorted(root / name for name in (
                "src/runtime/worker.py", "src/runtime/new.py",
                "scripts/dev/audit.py", "tests/test_worker.py",
            ))
            for package_root in ("src/runtime", "./src/runtime/"):
                with self.subTest(package_root=package_root):
                    scopes = (package_root, "scripts/dev", "tests")
                    self.assertEqual(discover_python_files(root, scopes), expected)
                    result = scan_repository(root, scopes)
                    self.assertEqual(result.functions_over_100, 1)
                    self.assertEqual(result.largest_functions[0].name, "large")

    def test_cli_explicit_root_and_ratchet_exit_contract(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src/example.py").write_text("pass\n", encoding="utf-8")
            baseline = root / "baseline.json"
            output = io.StringIO()
            arguments = ["--root", str(root), "--no-git", "--json"]
            with redirect_stdout(output):
                self.assertEqual(main([*arguments, "--write-baseline", str(baseline)]), 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["python_files"], 1)
            self.assertEqual(payload["roots"], ["src", "scripts", "tests"])
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([*arguments, "--ratchet", "--baseline", str(baseline)]), 0)
            (root / "src/new.py").write_text("pass\n", encoding="utf-8")
            with redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(main([*arguments, "--ratchet", "--baseline", str(baseline)]), 1)
            self.assertIn("python_files: 2 > baseline 1", errors.getvalue())
            with redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(main([*arguments, "--ratchet"]), 2)
            self.assertIn("--ratchet requires --baseline", errors.getvalue())

    def test_explicit_scopes_accept_multiple_repository_directories(self):
        args = parse_args(["--scope", "src/research_code_quality", "--scope", "tests"])

        self.assertEqual(args.scope, ["src/research_code_quality", "tests"])

    def test_explicit_package_scope_discovers_this_repository_code(self):
        repo_root = Path(__file__).resolve().parents[1]

        files = discover_python_files(
            repo_root,
            roots=("src/research_code_quality",),
            use_git=True,
        )

        self.assertIn(repo_root / "src/research_code_quality/scanner.py", files)

    def test_default_scopes_remain_compatible_with_downstream_repositories(self):
        self.assertEqual(DEFAULT_ROOTS, ("src", "scripts", "tests"))

    def test_ratchet_detects_only_increases_in_shared_metrics(self):
        repo_root = Path(__file__).resolve().parents[1]
        result = scan_repository(repo_root, roots=("src/research_code_quality",), use_git=True)

        self.assertEqual(
            ratchet_violations(result, {"metrics": {"python_files": result.python_files}}), []
        )
        self.assertEqual(
            ratchet_violations(result, {"metrics": {"python_files": result.python_files - 1}}),
            [f"python_files: {result.python_files} > baseline {result.python_files - 1}"],
        )

    def test_baseline_writer_emits_compact_json(self):
        repo_root = Path(__file__).resolve().parents[1]
        result = scan_repository(repo_root, roots=("src/research_code_quality",), use_git=True)

        with TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            write_baseline(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["metrics"]["python_files"], result.python_files)
        self.assertNotIn("functions", payload)


if __name__ == "__main__":
    unittest.main()
