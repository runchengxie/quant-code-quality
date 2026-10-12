# quant-code-quality

[English README](README.md)

`quant-code-quality` 提供多个量化研究仓库共用的 Python 可维护性扫描能力，减少重复实现和指标口径漂移。

本项目属于 Quant Research 项目系列，是供其他仓库使用的开发工具。它只提供通用扫描逻辑，各仓库仍自行维护适合本项目的指标和预算。

要求 Python 3.10 或更新版本，CI 使用 Python 3.11。

## 快速试用

使用 `uv` 安装开发依赖并运行扫描：

```bash
uv sync --locked --extra dev
uv run --locked --extra dev research-code-quality --root . --scope src/research_code_quality --scope tests --json
```

扫描其他仓库时显式指定 `--root`。默认根目录从扫描器模块位置查找，不保证是调用者的当前目录。

## 文档

- [使用与集成说明](docs/zh-CN/usage.md)：扫描内容、在其他项目中使用和验证方式
- [开发规则](AGENTS.md)：维护范围和提交前检查
