# Usage and integration

[中文页面](zh-CN/usage.md)

`research-code-quality` provides common static scanning for research repositories. It extracts algorithms previously duplicated in `alpha-research`, `portfolio-backtester`, `strategy-pipeline`, and `quant-execution-engine`.

## Ownership and API

The package discovers Python files with `discover_python_files`, measures file and function lengths with `scan_repository`, counts Ruff C901 per-file ignores, and returns a `ScanResult`. `to_payload()` includes metric thresholds and per-file/function records.

Consumers retain their own `Metrics` dataclasses, additional indicators, scan scopes, ratchet budgets, and output formatting. The scanner does not enforce a common budget across projects.

```python
from research_code_quality.scanner import scan_repository

result = scan_repository(repo_root, roots, limit)
```

`repo_root` is a `Path`, `roots` is a sequence of directory names, and `limit` defaults to `10`. Nested scopes such as `("src/ticknet", "scripts/dev", "tests")` work. Git discovery includes tracked and non-ignored untracked files, and matches directory boundaries: `src/ticknet_extra` is outside `src/ticknet`. Older versions only matched the first path component. Review newly scanned files before changing a baseline.

Repeated or overlapping scopes count each discovered path once in both Git and filesystem discovery. Filesystem discovery still includes ignored files. Deduplication corrects repeated counts; it does not change the metric thresholds or approve a consumer baseline.

## Install in a consumer

Use a valid PEP 508 direct reference in an optional dependency list, pinned to a reviewed commit:

```toml
[project.optional-dependencies]
dev = [
    "research-code-quality @ git+https://github.com/runchengxie/quant-code-quality.git@d0e86fc65be241b5e6c3996b99ef2864a6c85b94",
]
```

The workspace dependency configurations identify `quant-market-data-platform`, `quant-platform`, `quant-research`, and `quant-deep-learning` (local directory `deep-learning-tick-data-prediction`) as consumers. The deep-learning project retains the historical `research-code-quality.git` URL in its dependency pin. Each pins its own version in project configuration and its lockfile. This example does not upgrade those consumers. Check their actual pins and run their local gates independently before upgrading. A discovery fix may increase metrics without adding code; do not automatically relax budgets.

## CLI boundaries

Pass `--root .` when running an installed scanner in a consumer. Automatic root discovery starts from the scanner module location and may select the package checkout instead of the caller's repository.

```bash
uv run --locked --extra dev research-code-quality --root . --scope src --scope tests --json
```

`--scope` is repeatable and defaults to `src`, `scripts`, and `tests`. `--no-git` uses filesystem discovery without Git ignore rules. `--limit` defaults to `10` and only truncates the largest-file/function lists, not aggregate metrics. Invalid Python syntax still contributes file and line counts but produces no function metrics. This scanner does not replace lint or type checking.

`--ratchet --baseline PATH` rejects increases only for recorded metrics; omitted metrics are not checked. It returns `1` for an increase, `2` for a missing or unreadable baseline, and `0` on success. `--write-baseline PATH` writes JSON with `schema_version: 1`. Callers must review and store it appropriately; writing a baseline does not approve a new budget.

When both options are supplied, the scanner compares the existing baseline before writing. A failed comparison or invalid baseline leaves the baseline and write destination unchanged, even when both paths name the same file. A successful comparison may refresh the baseline as explicitly requested. Without `--ratchet`, baseline writing remains an explicit snapshot operation.

Create a first baseline with a separately reviewed `--write-baseline` command, then use `--ratchet` against it. Combining both options no longer creates a missing comparison baseline and then checks against that new snapshot.

Present known baseline metrics must be JSON integers. Booleans, `null`, strings and floating-point values return `2` in the CLI. Replace invalid values with reviewed integer budgets, or omit a metric if it is intentionally outside this comparison. Baseline `roots` and `schema_version` are metadata, not scope-validation gates; consumers must keep the intended scan scope consistent. The example Git pin above is historical and does not automatically deliver these fixes to consumers.

## Validation

```bash
uv run --locked --extra dev ruff check .
uv run --locked --extra dev python -m unittest discover -s tests -v
uv run --locked --extra dev python -m research_code_quality.scanner --root . --scope src/research_code_quality --scope tests --json
```

Runtime output is English or structured data; there is no locale option. CI uses Python 3.11; the package requires Python 3.10 or newer. There is no configured type checker, coverage threshold, or local dependency vulnerability gate. GitHub configures CodeQL and Dependabot; their presence does not establish a successful local security check.
