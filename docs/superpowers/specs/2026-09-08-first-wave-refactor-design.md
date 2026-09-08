# 第一波跨仓重构设计

## 目标

以 GitHub 当前 `main` 为唯一远端基线，推进三项低风险、可独立审查、可独立回滚的改动，并确保这些改动不依赖现有本地脏 worktree。

第一波只覆盖：

1. `quant-intel-platform`：修复 `docs/cashflow-feishu-shadow.md` 的乱码和普通说明语言不一致问题。
2. `quant-code-quality`：重新建立当前 `main` 的 Ruff 格式基线，只提交仍然存在的机械格式改动。
3. `quant-data-maintenance`：重新建立当前 `main` 的 Ruff 格式基线，只提交仍然存在的机械格式改动。

## 当前远端基线

设计以 2026-09-08 核对到的远端状态为起点：

- `quant-code-quality/main`：`d0ca440edf0197976c091c8e8c1b41c281f00f26`
- `quant-data-maintenance/main`：`15256019875841e05c110110f1d351e390b251ab`
- `quant-intel-platform/main`：`9e74066712654f40afaad9a89003c73f5654aa81`

执行每个任务前必须重新读取对应仓库的 `main`。如果 `main` 已推进，任务分支必须从新的远端头创建，不能继续使用以上 SHA 作为写入基线。

## 已确认事实

### `quant-intel-platform`

`docs/cashflow-feishu-shadow.md` 当前内容存在 UTF-8 文本被错误解释后形成的 mojibake，例如标题和中文段落显示为 `ç°é...`。文件后半段同时存在英文部署说明。

本任务只修正文档内容，不修改现金流策略、Feishu 发送逻辑、systemd timer、部署脚本或环境变量语义。

### GitHub Actions

`quant-intel-platform`、`quant-intel-deploy` 和 `quant-research` 的近期失败仍表现为 job 已结束、`steps` 为空。第一波不通过代码修改尝试解决该问题，也不修改 Actions workflow。

## PR 设计

### PR 1：`quant-intel-platform` 文档修复

**分支建议：** `docs/fix-cashflow-feishu-shadow-encoding`

**允许修改：**

- `docs/cashflow-feishu-shadow.md`

**改动规则：**

- 将乱码恢复为可读中文。
- 将普通说明段落统一为中文。
- 保留代码块、命令、路径、环境变量名、schema 名、CLI 参数、timer 名称和确认字符串的原始拼写。
- 保持既有行为语义，包括 test-group-only 限制、`CASHFLOW_SEND`、`CASHFLOW_SEND_CONFIRMATION`、PIT audit 和 publication receipt 约束。
- 不顺手修改其他文档。
- 不修改 Python、Shell、YAML 或 systemd 文件。

**验证：**

- 检查 Markdown 结构和代码块完整性。
- 搜索文件，确认不再存在当前 mojibake 特征文本。
- 如果仓库已有文档检查命令，执行现有命令并记录结果。
- 不把 GitHub Actions runner 类失败解释为本次文档变更失败。

### PR 2：`quant-code-quality` 格式基线

**分支建议：** `style/refresh-ruff-format-baseline`

**允许修改：**

- 仅修改当前 `main` 上由仓库既有 Ruff formatter 产生差异的 Python 文件。

**改动规则：**

- 先执行仓库现有的 Ruff lint 和 format check。
- 只有 format check 确认存在差异时才运行 formatter。
- 不改变 Ruff 配置、不新增 ignore、不修改测试逻辑、不做命名或结构重构。
- 如果当前 `main` 已经没有格式差异，则不创建空 PR。

**验证：**

- Ruff lint 通过。
- Ruff format check 通过。
- 如果仓库已有可执行测试，运行现有测试并记录结果。
- `git diff` 只包含 formatter 机械改动。

### PR 3：`quant-data-maintenance` 格式基线

**分支建议：** `style/refresh-ruff-format-baseline`

**允许修改：**

- 仅修改当前 `main` 上由仓库既有 Ruff formatter 产生差异的 Python 文件。

**改动规则：**

- 先执行仓库现有的 Ruff lint 和 format check。
- 只有 format check 确认存在差异时才运行 formatter。
- 不改变 Ruff 配置、不新增 ignore、不修改数据维护行为、不做结构重构。
- 如果当前 `main` 已经没有格式差异，则不创建空 PR。

**验证：**

- Ruff lint 通过。
- Ruff format check 通过。
- 如果仓库已有可执行测试，运行现有测试并记录结果。
- `git diff` 只包含 formatter 机械改动。

## 隔离与 Git 约束

每个仓库独立执行：

1. 重新读取 GitHub 远端 `main` 头。
2. 使用隔离 worktree 或等价隔离工作区，从该远端头创建任务分支。
3. 不复用用户现有的脏 worktree。
4. 不读取、搬运、暂存或提交用户现有未提交修改。
5. 不 force push。
6. 不删除本地或远端分支。
7. 不操作 production release worktree。
8. 不启用 auto-merge。
9. PR 初始状态为 draft。

如果远端 `main` 在任务执行期间推进，提交前比较任务分支与最新 `main`。存在冲突或语义重叠时停止该 PR 的写入推进，重新基于最新 `main` 评估。

## 明确排除范围

第一波不处理以下内容：

- production 当前 release 切换。
- `quant-intel-deploy` 的 release pin、manifest 或 lockfile 调整。
- GitHub Actions runner、额度、私有仓库权限或执行策略。
- `quant-platform` 的本地领先提交 reconciliation。
- `quant-intel-deploy`、`quant-intel-platform`、`quant-research` 的现有脏 worktree。
- Ruff、ty、coverage、`noqa` 门槛收紧。
- 大函数拆分、模块迁移、跨仓接口重构。

## PR 描述要求

每个实际 PR 必须记录：

- 分支创建时的 `main` SHA。
- 修改范围。
- 明确排除范围。
- 本地执行的验证命令和结果。
- GitHub Actions 若出现 `steps` 为空的 runner 类失败，单独标注为基础设施阻塞，不归因为本次改动。

## 成功标准

第一波完成时应满足：

- `quant-intel-platform` 的目标文档可正常阅读，且没有行为文件改动。
- 两个格式任务仅在当前 `main` 确认存在格式差异时产生 PR。
- 所有已创建 PR 都是小范围 draft PR，可独立审查和回滚。
- 没有 production、脏 worktree、历史本地提交或 CI 基础设施配置被意外修改。

## 回滚策略

每个 PR 独立提交、独立合并。任何一个 PR 出现问题时，只回滚对应 PR，不要求联动回滚其他仓库。文档 PR 不承担部署版本迁移职责；格式 PR 不承担行为修复职责。
