# quant-code-quality

[中文 README](README.zh-CN.md)

Shared Python maintainability scanning for quantitative research repositories. The package owns file discovery and common static metrics. Consumers own their scan scopes, additional metrics, budgets, and baselines.

Requires Python 3.10 or newer. CI runs on Python 3.11.

## Try it

```bash
uv sync --locked --extra dev
uv run --locked --extra dev research-code-quality --root . --scope src/research_code_quality --scope tests --json
```

Use `--root` when scanning another repository. The default root is detected from the installed scanner module, rather than necessarily from the current directory.

## Documentation

- [Usage and integration](docs/usage.md): metrics, CLI boundaries, dependency examples, and checks
- [Development rules](AGENTS.md): maintenance scope and required validation
