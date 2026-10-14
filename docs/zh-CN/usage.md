# quant-code-quality 使用与集成说明

[English page](../usage.md)

多个量化仓库共享的静态可维护性指标扫描库。

## 背景

`alpha-research`、`portfolio-backtester`、`strategy-pipeline`、`quant-execution-engine`
这些代码域原本各自持有一份几乎相同的 `scripts/dev/maintainability_metrics.py`
（发现 Python 文件、用 `ast` 统计函数长度、读取 `pyproject.toml` 的
`per-file-ignores` 计数 C901 豁免等）。本仓抽取其中稳定且跨仓一致的部分，
避免同一算法在多处漂移。

## 设计边界

本仓统一文件发现和通用静态指标，包括文件与函数长度、Ruff C901 按文件忽略项数量。
扫描结果以 `ScanResult` 返回，`to_payload()` 包含阈值以及文件和函数级记录。

各消费仓库仍保留自己的 `Metrics` dataclass、额外指标、扫描范围、ratchet 预算和输出格式。
扫描器不会在不同项目间统一执行预算。

## 消费方式

消费仓库可在 `pyproject.toml` 中把本仓作为 Git 依赖加入开发依赖：

```toml
[project.optional-dependencies]
dev = [
    "research-code-quality @ git+https://github.com/runchengxie/quant-code-quality.git@d0e86fc65be241b5e6c3996b99ef2864a6c85b94",
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

重复或重叠范围在 Git 和文件系统扫描中都只计入同一路径一次。文件系统扫描仍会纳入被 Git 忽略的文件。去重修正重复计数，不改变指标阈值，也不批准消费方基线。

## 消费方与升级约定

工作区依赖配置显示，`quant-market-data-platform`、`quant-platform`、`quant-research` 和 `quant-deep-learning`（本地目录 `deep-learning-tick-data-prediction`）使用本仓的开发依赖。深度学习项目的依赖固定版本仍保留历史 `research-code-quality.git` URL。各消费仓库在自己的 `pyproject.toml` 和锁文件中固定版本，版本不会自动同步；升级时应先检查该仓的实际锁定提交，再逐仓更新并运行本地扫描与质量门禁。

本仓只负责扫描算法及其稳定接口。每个消费仓库继续拥有自己的指标字段、目录范围、ratchet 预算和基线。扫描器修正目录发现逻辑后，新增纳入的文件必须先复核，再决定是否更新本地基线；不能因为依赖升级自动放宽质量预算。新增或移除消费者时，应同步更新本节和消费方的开发依赖。

## 校验

```bash
uv run --locked --extra dev ruff check .
uv run --locked --extra dev python -m unittest discover -s tests -v
uv run --locked --extra dev python -m research_code_quality.scanner \
  --root . --scope src/research_code_quality --scope tests --json
```

scanner 默认扫描 `src`、`scripts`、`tests`，以兼容使用本仓库算法的研究与平台仓库。
本仓库自身把包放在 `src/research_code_quality`，校验命令显式指定该目录和 `tests`。

## CLI 边界

安装到其他项目后，显式传入 `--root .`。默认根目录从扫描器模块位置查找，不保证是调用者的当前目录。

```bash
uv run --locked --extra dev research-code-quality --root . --scope src --scope tests --json
```

`--scope` 可重复，默认范围是 `src`、`scripts`、`tests`。`--no-git` 改用文件系统扫描，不应用 Git ignore 规则。`--limit` 默认 `10`，只限制最大文件和函数列表的长度，不改变汇总指标。语法无效的 Python 文件仍计入文件和行数，但不生成函数指标；扫描器不能替代 lint 或类型检查。

`--ratchet --baseline PATH` 只拒绝已记录指标的增长，未记录的指标不会被检查。指标超限返回 `1`，缺少或无法读取 baseline 返回 `2`，成功返回 `0`。`--write-baseline PATH` 写入 `schema_version: 1` 的 JSON，由调用者审核并保存在合适的位置，不会自动批准新预算。

同时指定这两项时，扫描器先对比已有基线，再执行写入。对比失败或基线无效时，已有基线和写入目标都保持不变，包括两者指向同一文件的情况。对比通过后，可按显式请求更新基线。不指定 `--ratchet` 时，写入仍是显式的快照操作。

首次建立基线时，先单独审核并执行 `--write-baseline`，再用 `--ratchet` 对比。组合两项不会再先创建缺失的对比基线，然后对照这份新快照检查。

基线中已提供的已知指标必须是 JSON 整数。布尔值、`null`、字符串和浮点值会使 CLI 返回 `2`。应改为经过审核的整数预算；若某指标有意不参与对比，可省略该项。基线的 `roots` 和 `schema_version` 仅作为元数据，不校验范围，消费方须自行保持扫描范围一致。上文 Git 固定版本示例是历史版本，不会自动让消费方获得这些修复。

运行输出为英文或结构化数据，当前没有 locale 选项。CI 使用 Python 3.11，包要求 Python 3.10 或更新版本。仓库未配置类型检查、覆盖率阈值或本地依赖漏洞扫描门禁。GitHub 配置了 CodeQL 和 Dependabot，不能据此声称本地安全检查通过。
