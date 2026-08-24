---
name: travelpal-git-release
description: TravelPal 版本发布与 git 操作规范。涉及推送 GitHub（打 tag）、本地同步 main、或版本一致性核验时使用。它把项目 git 操作分成几层：日常开发只 commit；推送 GitHub 时打 tag 到 dev 触发自动 Release；本地同步走"切 main → 拉取 → 切 dev → merge"流程。发布前会先核验版本同步（pyproject/footer/README 三处），确保可推送再动手。
whenToUse: 用户说"推送 / 打 tag / 发布 v某版本 / 同步 main / 拉取 origin / 版本核验"或涉及 git commit、tag、push、merge 时使用。参考 docs/runbooks/git.md 的同时用本技能规范发布与同步流。
allowed-tools: read, edit, write, grep, glob, bash
---

# TravelPal Git 发布与操作规范

> 把所有 git 类操作按"分层"规整。核心：日常开发只 commit；推送 GitHub 才引入 tag 流；本地同步走固定流程。所有 tag 打到 dev 分支。
> 版本号采用**单一事实源**：以 **pyproject.toml 的 `version` 为唯一基准**，前端 footer 与 README 当前阶段对齐它。

## 一、版本格式（单一事实源）

- 格式：`vX.Y.Z`（正式）/ `vX.Y.Z-beta`（预发布，可选）。
- **起点 `v0.1.0`**（已是当前版本，三处对齐）。
- **tag 名**：`v0.1.0` 或 `v0.1.0-beta`（不带 v 前缀也行，但统一带）。
- **单一事实源**：版本一律以 pyproject.toml 的 `version` 为准。**核验 = 比对另两处是否跟基准一致。**
  - 基准：`pyproject.toml` → `version = "..."`
  - 对齐点1：前端 footer（`frontend/src/App.vue` 的 `.footer-version`）
  - 对齐点2：README 当前阶段（`README.md` Roadmap 的"当前阶段"行）
  - **不一致 → 阻断**，提醒对齐后再发布。

## 二、日常开发（只 commit）

- 遵循 docs/runbooks/git.md 的 commit 规范：`<type>: <中文描述>`。
- type：`feat` / `fix` / `docs` / `chore` / `refactor` / `test`。
- 在 `dev` 分支开发、提交、`push origin dev`。**不打 tag**。

## 三、推送 GitHub（引入 tag 流）

用户说"推送 vX.Y.Z / 打 tag / 发布"时，按此流：

1. **核验版本同步**（单一事实源）：
   - 读 pyproject.toml 的 `version`，确定基准版本。
   - 比对前端 footer 版本 → 若缺失，**提示"前端未标记版本，需先补"（不阻断）**；若与基准不符，**阻断**并提醒。
   - 比对 README 当前阶段 → 若与基准不符，**阻断**并提醒。
   - 确认本次要打的 tag（如 `v0.1.0`）与基准一致。
2. **检查 git status**：确认工作区干净（无未提交改动），可推送。有未提交改动则**提醒用户**，不擅自处理。
3. **打 tag 到 dev**：`git tag vX.Y.Z`（或 `-beta`）。
4. **推送**：`git push origin dev --tags`（触发 release.yml 自动生成 changelog + GitHub Release）。
5. **输出结果**：列出本次 tag、推送的分支、触发 Release 的预期。
   - **可选收尾**：提醒是否回写 README"当前阶段"为已发布版本。

## 四、本地同步（同步 main）

用户说"同步 main / 拉取 origin"时，按此流：

1. **先 `git status`**：确认本地无未提交改动，避免 merge 冲突。
2. **切到 main**：`git checkout main`
3. **拉取**：`git pull origin main`
4. **切回 dev**：`git checkout dev`
5. **merge**：`git merge main`
6. **消除差异**：处理冲突/对齐后 `git push origin dev`（如适用）。

## 五、红线

1. **不擅自改动版本**：只在用户让改时改，且以 pyproject 为基准同步另两处。
2. **不一致就提醒，不硬推**：版本对齐失败或工作区不干净时，提示用户，不擅自推送。
3. **不擅自 git commit/push/merge/tag**：这些是影响用户判断的操作，仅在用户明确要求时执行。
4. **tag 一律打到 dev**，不直接打 main。
5. **不越权读**：只读与发布相关的版本/状态，不全量读取无关历史。

## 口诀

> 日常只 commit；发布打 tag 到 dev、push 触发 Release；同步走"切main→pull→切dev→merge"。版本以 pyproject 为唯一源，发布前核验 footer + README。不一致就提醒，不硬推。
