---
name: travelpal-git-release
description: TravelPal 版本发布与 git 操作规范：日常只 commit、发布靠 GitHub 自动链路（CI + Docs → Deploy → Release，自动打 tag 指向 main）、本地同步流程。涉及 git 操作或发布时使用。
whenToUse:
  - 用户明确指令：推送、发布 v某版本、合并 dev 到 main、同步 main、拉取 origin、版本核验
  - 特定场景：涉及 git commit、tag、push、merge、PR 时
  - 关键词提及：git、push、tag、release、版本、PR、merge、commit
  - 不触发：与 git/发布无关的编码或文档任务
allowed-tools: read, edit, write, grep, glob, bash
---

# TravelPal Git 发布与操作规范

> 把所有 git 类操作按"分层"规整。核心：日常开发只 commit；**发布靠 GitHub 自动链路**（CI + Docs 并行 → Deploy → Release，tag 自动生成并指向 main），落地在流程最后；本地同步走固定流程。
> 版本号采用**单一事实源**：以 **pyproject.toml 的 `version` 为唯一基准**，前端 footer 与 README 当前阶段对齐它。tag 与 GitHub Release 由 release.yml 自动生成，**不手动打 tag、不手动 push tags**。

## 一、版本格式（单一事实源）

- 格式：`vX.Y.Z`（正式）/ `vX.Y.Z-beta`（预发布，可选）。
- **当前版本**（以 `pyproject.toml` 的 `version` 为准，三处应对齐）。
- **tag 名**：`v<version>` 或 `v<version>-beta`（不带 v 前缀也行，但统一带），由 release.yml 从 pyproject 自动生成。
- **单一事实源**：版本一律以 pyproject.toml 的 `version` 为准。**核验 = 比对另两处是否跟基准一致。**
  - 基准：`pyproject.toml` → `version = "..."`
  - 对齐点1：前端 footer（`frontend/src/App.vue` 的 `.footer-version`）
  - 对齐点2：README 当前阶段（`README.md` Roadmap 的"当前阶段"行）
  - **不一致 → 阻断**，提醒对齐后再发布。

## 二、日常开发（commit + 普通 push）

- commit 规范：`<type>: <中文描述>`。type：`feat` / `fix` / `docs` / `chore` / `refactor` / `test`。
- 在 `dev` 分支开发、提交；需要同步远程就**直接 `git push origin dev`**。
- **这是"普通同步"，不是发布**：**不写交接文档、不核验版本**。发布不靠 `push dev`（release 只监听 main 的 Deploy），因此 push dev 不会误触发发布。只有用户明确说"发布 / 合并 dev 到 main / 上线"时，才走「四」的发布流程。
- 分支：`main`=发布分支（只从 GitHub PR 合并）；`dev`=开发分支（所有工作在此提交）。当前早期阶段直接在 dev 开发，不设特性分支。

## 三、PR 规范（dev → main）

- PR 标题格式同 commit 规范。
- PR 描述包含：改了什么、为什么改、如何验证。
- 合并方式：统一 **Squash and merge**。
- **外部贡献（Fork 工作流）**：Fork 到个人账号 → 在 Fork 建分支提改进 → 向本仓库 `dev` 分支发 PR → PR 过 CI 后维护者合并。

## 四、发布（走 GitHub 自动链路，非手动打 tag）

> 发布**不手动 `git tag`、不 `git push --tags`**。tag 与 GitHub Release 由 `release.yml` 在 **Deploy 成功且由 main push 触发**后自动创建，落地在流程最后。
> 链路：**CI + Docs（并行）→ Deploy → Release**。开发者只需确保版本/发布正文/交接文档就绪，然后合并 dev → main（经 PR Squash and merge）触发整条链。

用户说"发布 / 合并 dev 到 main / 上线"时，按此流：

0. **确认交接文档已更新并阅读**（联动 session-handoff）：`docs/handoff/CURRENT_CODE.md`（或 `CURRENT_DOC.md`，视本次改动类型）需**已更新到最新**、反映本会话至今的完整事件并已阅读。若过期/未反映最新 → **先更新 → 再读 → 再继续**。详见 session-handoff 的"何时读 / 何时写"。
1. **核验版本同步**（单一事实源）：
   - 读 pyproject.toml 的 `version`，确定基准版本（如 `0.2.0`）；release.yml 会据此自动生成 tag `v0.2.0`。
   - 比对前端 footer 版本 → 若缺失，**提示"前端未标记版本，需先补"（不阻断）**；若与基准不符，**阻断**并提醒。
   - 比对 README 当前阶段 → 若与基准不符，**阻断**并提醒。
   - 确认将自动生成的 tag（`v<version>`）与基准一致。
2. **核验版本说明 `docs/releases/<tag>.md`**（`<tag>` = `v` + pyproject version，如 `v0.2.0`）：
   - 检查该文件是否**存在且内容非空**。
   - **缺失 → 阻断，不合并、不触发发布**。agent 基于本次 commit 提炼初稿 → 用户确认后写入。
   - agent 可提炼草稿，但**必须经用户确认**才算完成，不擅自落盘。
   - 该文件会被 release.yml 剥离 frontmatter 后作为 GitHub Release body 的唯一来源，无逐条 commit。
3. **检查 git 状态**：确认 dev 已就绪、`docs/releases/<tag>.md` 已提交。工作区不净则**提醒用户**，不擅自处理。
4. **合并 dev → main**：经 GitHub PR 走 **Squash and merge**（见「三」）。合并即触发整条自动链。
5. **说明预期**：main push 后 → CI（test+frontend）与 Docs 并行 → CI 成功后 Deploy 自动部署 → Deploy 成功后 release.yml 自动打 tag（`target_commitish` 指向被部署的 main commit，保证 tag/部署/发布三者对齐）并生成 GitHub Release，读 `docs/releases/<tag>.md`。
   - **可选收尾**：提醒是否回写 README"当前阶段"为已发布版本。

### 四.5 版本说明目录 `docs/releases/`

纯给 GitHub Actions 索引的版本说明存储，**不入文档站**（conf.py `exclude_patterns` 排除）、无 README、无 archive。

- **文件名 = tag 名**：`v<X.Y.Z>.md` 或 `v<X.Y.Z>-beta.md`，严格与 pyproject 的 version 一致。
- **每版本一份**，人工精炼。正文分两层：**「主要变化」**（面向读者，这版带来什么价值，偏 feat）+ **「主要修改」**（面向技术，具体改动明细，偏 fix）。**不逐条列 commit**。
- **frontmatter 规范**（与 docs/handoff 及各 md 模板一致）：开头用 `---`，其中 **date 必须**，`version`/`status` 可选。date 是 GitHub Release 原材料解析所需，也标注文档"生命"。

**内容模板**：用 `assets/release-template.md`（不留在 docs/，收敛于 skill；发布时复制为 `docs/releases/<tag>.md`）。

**release.yml 读取**：`docs/releases/<tag>.md`（`<tag>`=该 workflow 自动生成的 `v<version>`）作为 GitHub Release 的 body 唯一来源（取代 git-cliff 自动逐条），读取时用 awk 剥离 YAML frontmatter（首尾两条 `---` 之间），稳健处理模板注释块。缺文件**不阻断**release（出占位 Release），但规范要求**发布前补齐**。

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
4. **不手动打 tag，tag 由 release.yml 自动创建并指向 main 被部署的 commit**：不手动 `git tag` / `git push --tags`，避免"一打 tag 就提前发布"；tag 与部署、发布三者严格对齐。
5. **不越权读**：只读与发布相关的版本/状态，不全量读取无关历史。
6. **版本说明缺失即阻断**：`docs/releases/<tag>.md` 未就绪（不存在或空），不合并、不触发发布。
7. **不擅自生成/落盘发布正文**：agent 可提炼草稿，但必须用户确认后才写入；正文分"主要变化"（读者价值）与"主要修改"（技术明细），不逐条列 commit。
8. **发布前确认交接文档**：合并到 main 前须确认 `docs/handoff/CURRENT_*.md` 已更新并阅读（联动 session-handoff），否则读到的是过期状态。

## assets

- `assets/release-template.md` — 发布说明模板（复制为 `docs/releases/<tag>.md`）。

## 口诀

> 日常 commit + push dev（普通同步，不发布）；**发布=合并 dev→main 触发自动链**：CI + Docs 并行 → Deploy → Release（自动打 tag 指向 main、生成 GitHub Release）；同步 main 走"切main→pull→切dev→merge"。版本以 pyproject 为唯一源，发布前核验 footer + README + docs/releases 版本说明 + 交接文档（CURRENT_*）已更新并阅读。说明缺失就阻断，不硬推。
