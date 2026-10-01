# quant-code-quality 使用与集成说明

多个量化仓库共享的静态可维护性指标扫描库。

## 背景

`alpha-research`、`portfolio-backtester`、`strategy-pipeline`、`quant-execution-engine`
这些代码域原本各自持有一份几乎相同的 `scripts/dev/maintainability_metrics.py`
（发现 Python 文件、用 `ast` 统计函数长度、读取 `pyproject.toml` 的
`per-file-ignores` 计数 C901 豁免等）。本仓抽取其中稳定且跨仓一致的部分，
避免同一算法在多处漂移。

## 设计边界

本仓只拥有跨仓一致的部分：

- 发现仓库内的 Python 文件（`discover_python_files`）
- 用 `ast` 统计每个函数的起止行与长度（`_function_metrics_for_file`）
- 读取 `pyproject.toml` 统计 C901 按文件忽略数量（`_c901_file_ignore_count`）
- 汇总为 `ScanResult`（`scan_repository`）

各消费仓库或代码域的专属部分仍保留在各自项目中：

- `Metrics` dataclass（字段因仓库而异，例如 strategy-pipeline 多 `src/script/test_files_over_750`）
- ratchet 预算（`DEFAULT_RATCHET_BUDGETS`，是治理值，必须本地冻结）
- `command_run_functions_over_150` 等仓库专属指标的路径前缀
- `to_payload` 里的 `thresholds` 细节

这样既能消除真重复，又不会用 `__getattr__` 之类的魔法去强行统一差异字段。

## 消费方式

消费仓库可在 `pyproject.toml` 中把本仓作为 Git 依赖加入开发依赖：

```toml
[project.optional-dependencies]
dev = [
    "research-code-quality = { git = \"https://github.com/runchengxie/quant-code-quality.git\" }",
]
```

本地包装器只需：

```python
from research_code_quality.scanner import scan_repository

result = scan_repository(repo_root, roots, limit)
# 再补上本仓专属指标，组装出与原来一致的 Metrics 对象
```

`roots` 支持多层目录，例如 `("src/ticknet", "scripts/dev", "tests")`。
Git 扫描按完整目录边界匹配，包含已跟踪文件和未被忽略的未跟踪文件，
`src/ticknet_extra` 不属于 `src/ticknet` 范围。
旧版 Git 扫描仅匹配路径第一层，可能漏掉多层目录。升级后应核对新增纳入的
文件及原有基线。指标上升可能来自修正漏扫，不能自动重写基线视为通过。

## 消费方与升级约定

当前工作区中，`quant-market-data-platform`、`quant-platform` 和 `quant-research` 将本仓作为开发依赖使用。各消费仓库在自己的 `pyproject.toml` 和锁文件中固定版本，版本不会自动同步；升级时应先检查该仓的实际锁定提交，再逐仓更新并运行本地扫描与质量门禁。

本仓只负责扫描算法及其稳定接口。每个消费仓库继续拥有自己的指标字段、目录范围、ratchet 预算和基线。扫描器修正目录发现逻辑后，新增纳入的文件必须先复核，再决定是否更新本地基线；不能因为依赖升级自动放宽质量预算。新增或移除消费者时，应同步更新本节和消费方的开发依赖。

## 校验

```bash
uv run --group dev ruff check .
uv run --group dev python -m research_code_quality.scanner \
  --scope src/research_code_quality --scope tests --json
```

scanner 默认扫描 `src`、`scripts`、`tests`，以兼容使用本仓库算法的研究与平台仓库。
本仓库自身把包放在 `src/research_code_quality`，校验命令显式指定该目录和 `tests`。
