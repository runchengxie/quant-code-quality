# First Wave Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver three independent low-risk draft PRs from the latest remote `main`: repair one corrupted market-intel document, then refresh Ruff formatting baselines only where current repositories still contain formatter drift.

**Architecture:** Each repository is treated as an independent change unit with its own branch, verification evidence, commit, and draft PR. Every implementation branch is created from the then-current remote `main`; existing dirty local worktrees, production release worktrees, CI runner configuration, release pins, and behavioral refactors remain out of scope.

**Tech Stack:** Git/GitHub pull requests, Python 3.10+, uv, Ruff, unittest/pytest, setuptools build tooling, Markdown.

**Spec:** `docs/superpowers/specs/2026-09-08-first-wave-refactor-design.md`

## Global Constraints

- Re-read each repository's remote `main` immediately before creating its implementation branch.
- Do not reuse, stage, move, clean, or delete content from any existing dirty worktree.
- Do not modify production release worktrees, production release pins, manifests, lockfiles, GitHub Actions workflows, branch protection, runner settings, or CI permissions.
- Do not force-push, delete branches, enable auto-merge, or merge any PR.
- All implementation PRs start as draft PRs.
- If remote `main` advances before PR creation, compare the branch against the latest `main`; stop and rebase the task conceptually onto the new head if there is semantic overlap.
- A formatting task creates no branch or PR when the current `main` already passes Ruff format check.
- Verification claims require fresh command output from the exact tree being proposed.

---

### Task 1: Repair the cashflow Feishu shadow document

**Files:**
- Modify: `quant-intel-platform/docs/cashflow-feishu-shadow.md`

**Interfaces:**
- Consumes: existing documentation contract for `strategy_app.cashflow.selection.v1`, `strategy_pipeline.cashflow.publication.v1`, `cashflow-delivery`, `run_cashflow_shadow.sh`, `CASHFLOW_SEND`, `CASHFLOW_SEND_CONFIRMATION`, and the PIT audit flow.
- Produces: the same operational instructions in readable Chinese, with commands, schema names, paths, environment variables, timer names, and confirmation strings unchanged.

- [ ] **Step 1: Refresh repository rules and base SHA**

Read `AGENTS.md` and `docs/cashflow-feishu-shadow.md` from current remote `main`. Record the current `main` SHA. Confirm that `docs/AGENTS.md` does not override the root rules.

Expected constraint: implementation branch must use the repository-approved `fix/*` prefix.

- [ ] **Step 2: Create an isolated implementation branch**

Create `fix/cashflow-feishu-shadow-encoding` from the current remote `main`. Do not use an existing local development or production worktree.

- [ ] **Step 3: Replace only the corrupted document text**

Rewrite `docs/cashflow-feishu-shadow.md` so that:

```text
# 现金流策略飞书 Shadow 推送
```

is the heading; the selection and publication constraints remain unchanged; the scheduled shadow bridge section is written in Chinese; and all literal commands, paths, schema names, CLI flags, environment variables, timer names, and `I_UNDERSTAND_TEST_GROUP_ONLY` remain byte-for-byte unchanged inside prose/code where applicable.

Do not change any other file.

- [ ] **Step 4: Verify document integrity locally**

Run:

```bash
python -c "from pathlib import Path; p=Path('docs/cashflow-feishu-shadow.md'); t=p.read_text(encoding='utf-8'); assert '# 现金流策略飞书 Shadow 推送' in t; assert 'ç°é' not in t; assert 'ï¼' not in t; assert 'ã' not in t; assert t.count('```') % 2 == 0"
```

Expected: exit code 0.

Then run the repository's lightweight static gates that do not require production data:

```bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python project_tools/update_cli_help.py --check
```

Record every result exactly. Do not run live delivery, market-data refresh, scheduler installation, or production smoke commands.

- [ ] **Step 5: Review the diff**

Confirm the diff contains exactly one changed file: `docs/cashflow-feishu-shadow.md`. Confirm no command, schema, environment variable, path, timer, or confirmation token was accidentally changed.

- [ ] **Step 6: Commit and open a draft PR**

Commit with:

```text
docs: repair cashflow shadow guide encoding
```

Open a draft PR against `main` titled:

```text
docs: repair cashflow shadow guide encoding
```

The PR body must include the branch base SHA, one-file scope, explicit exclusions, exact local verification commands/results, and a note that runner failures with empty `steps` are infrastructure blockers rather than evidence against this documentation-only change.

---

### Task 2: Refresh the quant-code-quality Ruff format baseline

**Files:**
- Modify: only Python files changed by the repository's current Ruff formatter, and only if the pre-change format check fails.

**Interfaces:**
- Consumes: `pyproject.toml` Ruff configuration (`target-version = py312`, `line-length = 100`, existing lint selection).
- Produces: formatter-equivalent Python source with unchanged behavior and unchanged Ruff configuration.

- [ ] **Step 1: Refresh base SHA and repository contents**

Read current remote `main`, `pyproject.toml`, `README.md`, and `tests/test_scanner.py`. Record the current `main` SHA.

- [ ] **Step 2: Establish the pre-change quality baseline**

In an isolated checkout of the current `main`, run:

```bash
uv run --group dev ruff check .
uv run --group dev ruff format --check .
uv run --group dev python -m unittest discover -s tests -v
uv run --group dev python -m research_code_quality.scanner --scope research_code_quality --scope tests --json
```

If `ruff format --check .` exits 0, record that the old formatting finding is stale and stop Task 2 without creating an implementation branch or PR.

- [ ] **Step 3: Create the formatting branch only when drift exists**

If and only if the format check fails because files would be reformatted, create `style/refresh-ruff-format-baseline` from the same recorded current `main` SHA.

- [ ] **Step 4: Apply only Ruff formatter output**

Run:

```bash
uv run --group dev ruff format .
```

Do not edit `pyproject.toml`, tests, naming, imports beyond Ruff's own formatter output, or program structure manually.

- [ ] **Step 5: Verify the formatted tree**

Run fresh:

```bash
uv run --group dev ruff check .
uv run --group dev ruff format --check .
uv run --group dev python -m unittest discover -s tests -v
uv run --group dev python -m research_code_quality.scanner --scope research_code_quality --scope tests --json
```

Expected: all four commands exit 0.

- [ ] **Step 6: Review formatter-only diff**

Confirm every changed file is Python source and every hunk is mechanical formatting. If any semantic change appears, discard that hunk and regenerate from the untouched base rather than hand-correcting it.

- [ ] **Step 7: Commit and open a draft PR**

Commit with:

```text
style: refresh Ruff formatting baseline
```

Open a draft PR against `main` with the same title. Include base SHA, exact changed filenames, pre-change format-check result, post-change verification output, and the explicit statement that no Ruff configuration or behavior changed.

---

### Task 3: Refresh the quant-data-maintenance Ruff format baseline

**Files:**
- Modify: only Python files changed by the repository's current Ruff formatter, and only if the pre-change format check fails.

**Interfaces:**
- Consumes: root `AGENTS.md` safety rules and `pyproject.toml` Ruff configuration (`target-version = py311`, `line-length = 100`).
- Produces: formatter-equivalent maintenance source/tests with unchanged audit/consolidate behavior and unchanged CLI surface.

- [ ] **Step 1: Refresh repository rules and base SHA**

Read current remote `main`, root `AGENTS.md`, and `pyproject.toml`. Record the current `main` SHA.

- [ ] **Step 2: Establish the pre-change quality baseline**

In an isolated checkout of the current `main`, run:

```bash
uv run --locked --extra dev ruff check .
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev pytest
uv run --locked --extra dev python -m build
```

Do not run `consolidate --apply` or any command against real data paths.

If `ruff format --check .` exits 0, record that the old formatting finding is stale and stop Task 3 without creating an implementation branch or PR.

- [ ] **Step 3: Create the formatting branch only when drift exists**

If and only if the format check reports files would be reformatted, create `style/refresh-ruff-format-baseline` from the same recorded current `main` SHA.

- [ ] **Step 4: Apply only Ruff formatter output**

Run:

```bash
uv run --locked --extra dev ruff format .
```

Do not alter Ruff configuration, CLI names/arguments, audit/consolidate semantics, data-path safeguards, documentation, or tests manually.

- [ ] **Step 5: Verify the formatted tree**

Run fresh:

```bash
uv run --locked --extra dev ruff check .
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev pytest
uv run --locked --extra dev python -m build
```

Expected: all four commands exit 0.

- [ ] **Step 6: Review formatter-only diff**

Confirm every changed file is Python source and every hunk is mechanical formatting. Confirm no file-path operation, SHA-256 validation, audit behavior, consolidate planning, or CLI behavior changed.

- [ ] **Step 7: Commit and open a draft PR**

Commit with:

```text
style: refresh Ruff formatting baseline
```

Open a draft PR against `main` with the same title. Include base SHA, exact changed filenames, pre-change format-check result, post-change verification output, and an explicit note that no data operation was executed.

---

## Final review checklist

- [ ] Re-read the approved spec and confirm Tasks 1-3 cover every first-wave requirement.
- [ ] Confirm no plan step modifies production, runner/workflow configuration, release pins, dirty worktrees, branch protection, or `quant-platform` reconciliation state.
- [ ] Confirm no empty implementation PR was created when a formatting baseline was already clean.
- [ ] Confirm every created implementation PR is draft, targets `main`, and contains fresh verification evidence.
- [ ] Confirm no PR was merged and auto-merge remains disabled.
