# 项目协作规则

## 多智能体协作流程（必须遵守）

### 任务隔离

- 每个任务、每个智能体必须使用独立的任务分支和独立的 Git worktree。开始前检查仓库说明、`git status --short` 和 `git worktree list`，确认任务范围和已有工作归属。
- 先执行 `git fetch origin`，再从最新的 `origin/main` 创建任务分支和仓库外部的临时 worktree。分支名和目录名应包含任务或智能体标识，避免重用其他任务的名称。
- 所有编辑、验证、提交和推送都在自己的任务 worktree 中完成。禁止直接在 `main` 上修改、提交或推送，禁止共用、切换或清理其他智能体的分支和 worktree。
- 保留已有修改、未跟踪文件和其他任务状态。发现归属不明或重叠修改时停止相关操作，说明阻塞原因，不擅自覆盖。
- Git hooks 和仓库配置可能由多个 worktree 共享。不得修改共享 hooks、`core.hooksPath` 或通过配置、环境变量、`--no-verify` 等方式绕过现有检查。
- 生产运行目录、持久数据、定时任务依赖和长期产物必须放在临时 worktree 之外的稳定位置。不得让生产服务或数据依赖将被清理的任务目录。

### 验证、提交和合并

- 提交前和推送前必须完成与改动相符的测试与验证，查看实际结果。纯文档改动至少检查 `git diff --check`、内容准确性、已有说明是否保留以及变更文件范围，同时遵守本仓库已有验证要求和 hooks。
- 仅提交本任务文件，检查暂存差异后提交，推送自己的任务分支，并创建目标为 `main` 的 PR。PR 中写明变更内容、实际执行的验证及其结果。
- 等待 PR 检查完成，仅在所有适用检查通过、没有合并冲突且满足仓库审查规则时合并。失败、待定或无法确认的检查不得视为通过，不得强制合并或绕过保护规则。
- 如需更新任务分支，在自己的 worktree 中合并最新 `origin/main`，处理冲突后重新验证并正常推送。禁止强制推送、强制删除或使用破坏性 reset。

### 合并确认和清理

- 清理前必须查询远端 PR，确认状态为 `MERGED`、目标为 `main`，并记录 PR URL 和合并 SHA。重新 fetch 后确认该合并提交已包含在 `origin/main` 中，不能仅凭本地合并、关闭 PR 或推送成功判断完成。
- 检查任务 worktree 状态，包括未跟踪和忽略文件，确认没有需要保留的工作、长期产物或仍依赖该目录的进程。存在疑问时保留现场并报告。
- 只清理本任务创建且已核实合并的远端分支、本地分支和 worktree。远端任务分支若未被平台自动删除，使用 `git push origin --delete <task-branch>` 删除。
- 先从 worktree 外使用 `git worktree remove <task-worktree>` 移除自己的 worktree，再使用 `git branch -d <task-branch>` 删除本地分支，禁止删除仍检出的分支。不得使用 `--force`、`git branch -D`、批量清理或破坏性 reset。
- squash 或 rebase 合并可能使本地 `-d` 无法识别分支已合并。此时保留分支并报告，不强制删除。任一清理步骤受阻时保留尚未清理的任务状态并说明具体原因。
- 不修改主检出目录或其他智能体的 worktree。只有在明确允许、主检出目录干净且无人使用时，才可执行可选的 `--ff-only` 同步。
- 完成后报告 PR URL、远端合并 SHA、实际验证结果、变更文件和清理结果。

## 验证命令

遵循现有 CI，提交前运行：

```bash
uv run --locked --extra dev ruff check .
python -m unittest discover -s tests -v
uv run --locked --extra dev python -m research_code_quality.scanner \
  --scope research_code_quality --scope tests --json
```
