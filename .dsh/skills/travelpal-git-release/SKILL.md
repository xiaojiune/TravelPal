---
name: travelpal-git-release
description: TravelPal 版本发布与 git 操作规范。涉及推送 GitHub（打 tag）、本地同步 main、或版本一致性核验时使用。它把项目 git 操作分成几层：日常开发只 commit；推送 GitHub 时打 tag 到 dev 触发自动 Release；本地同步走"切 main → 拉取 → 切 dev → merge"流程。发布前会先核验版本同步（pyproject/footer/README 三处），确保可推送再动手。
whenToUse: 用户说"推送 / 打 tag / 发布 v某版本 / 同步 main / 拉取 origin / 版本核验"或涉及 git commit、tag、push、merge、PR 时使用，用于规范发布、同步与 PR 流程。
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

- commit 规范：`<type>: <中文描述>`。
- type：`feat` / `fix` / `docs` / `chore` / `refactor` / `test`。
- 在 `dev` 分支开发、提交、`push origin dev`。**不打 tag**。
- 分支：`main`=发布分支（只从 GitHub PR 合并）；`dev`=开发分支（所有工作在此提交）。当前早期阶段直接在 dev 开发，不设特性分支。

## 三、PR 规范（dev → main）

- PR 标题格式同 commit 规范。
- PR 描述包含：改了什么、为什么改、如何验证。
- 合并方式：统一 **Squash and merge**。
- **外部贡献（Fork 工作流）**：Fork 到个人账号 → 在 Fork 建分支提改进 → 向本仓库 `dev` 分支发 PR → PR 过 CI 后维护者合并。

## 四、推送 GitHub（引入 tag 流）

用户说"推送 vX.Y.Z / 打 tag / 发布"时，按此流：

1. **核验版本同步**（单一事实源）：
   - 读 pyproject.toml 的 `version`，确定基准版本。
   - 比对前端 footer 版本 → 若缺失，**提示"前端未标记版本，需先补"（不阻断）**；若与基准不符，**阻断**并提醒。
   - 比对 README 当前阶段 → 若与基准不符，**阻断**并提醒。
   - 确认本次要打的 tag（如 `v0.1.0`）与基准一致。
2. **核验版本说明 `docs/releases/<tag>.md`**：
   - 检查该文件是否**存在且内容非空**。
   - **缺失 → 阻断，不推送、不打 tag**。agent 基于本次 commit 提炼初稿 → 用户确认后写入。
   - agent 可提炼草稿，但**必须经用户确认**才算完成，不擅自落盘。
3. **检查 git status**：确认工作区干净 + `docs/releases/<tag>.md` 已提交。不干净则**提醒用户**，不擅自处理。
4. **打 tag 到 dev**：`git tag vX.Y.Z`（或 `-beta`）。
5. **推送**：`git push origin dev --tags`（触发 release.yml 读取 docs/releases/<tag>.md 生成 GitHub Release）。
6. **输出结果**：列出本次 tag、推送的分支、触发 Release 的预期。
   - **可选收尾**：提醒是否回写 README"当前阶段"为已发布版本。

### 四.5 版本说明目录 `docs/releases/`

纯给 GitHub Actions 索引的版本说明存储，**不入文档站**（conf.py `exclude_patterns` 排除）、无 README、无 archive。

- **文件名 = tag 名**：`v<X.Y.Z>.md` 或 `v<X.Y.Z>-beta.md`，严格与 pyproject 的 version 及要打的 tag 一致。
- **每版本一份**，人工精炼，只写"这个版本带来了什么"，**不逐条列 commit**。

**内容模板**：用 `assets/release-template.md`（不留在 docs/，收敛于 skill；发布时复制为 `docs/releases/<tag>.md`）。

**release.yml 读取**：`docs/releases/${GITHUB_REF_NAME}.md` 作为 GitHub Release 的 body 唯一来源（取代 git-cliff 自动逐条）。缺文件**不阻断**release（出占位 Release），但规范要求**推送前补齐**。

## 五、本地同步（同步 main）

用户说"同步 main / 拉取 origin"时，按此流：

1. **先 `git status`**：确认本地无未提交改动，避免 merge 冲突。
2. **切到 main**：`git checkout main`
3. **拉取**：`git pull origin main`
4. **切回 dev**：`git checkout dev`
5. **merge**：`git merge main`
6. **消除差异**：处理冲突/对齐后 `git push origin dev`（如适用）。

## 六、红线

1. **不擅自改动版本**：只在用户让改时改，且以 pyproject 为基准同步另两处。
2. **不一致就提醒，不硬推**：版本对齐失败或工作区不干净时，提示用户，不擅自推送。
3. **不擅自 git commit/push/merge/tag**：这些是影响用户判断的操作，仅在用户明确要求时执行。
4. **tag 一律打到 dev**，不直接打 main。
5. **不越权读**：只读与发布相关的版本/状态，不全量读取无关历史。
6. **版本说明缺失即阻断**：`docs/releases/<tag>.md` 未就绪（不存在或空），不推送、不打 tag。
7. **不擅自生成/落盘发布正文**：agent 可提炼草稿，但必须用户确认后才写入；正文只写"主要修改"，不铺列 commit。

## assets

- `assets/release-template.md` — 发布说明模板（复制为 `docs/releases/<tag>.md`）。

## 口诀

> 日常只 commit；发布打 tag 到 dev、push 触发 Release；同步走"切main→pull→切dev→merge"。版本以 pyproject 为唯一源，发布前核验 footer + README + docs/releases 版本说明。说明缺失就阻断，不硬推。
