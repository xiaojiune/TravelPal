---
task: "TravelPal 文档站重建：ADR 重编号、structure 模板化、index.rst 收敛，均已完成并待 review"
status: "in-progress"
date: "2026-08-26"
version: ""
---
# 文档会话交接

## 上一段进行到哪

本会话完成了一套文档站（docs/）的大规模翻修，**均已落到 dev 分支**，其中部分已提交、部分待 review：

### 已提交（经 git log 确认在上游）

- 1. **ADR 重编号并修正引用**（`8ea4807`）：docs/ADR/ 现存 9 篇重排为连续 001-009（005→004、006→005、007→006、009→007、012→008、014→009）；交叉引用同步更新，历史引用（原 ADR-008/010/011/013 已归入 design/ 或已删）改为纯文字描述避免撞号。
- 2. **代码注释 ADR 编号修正**（`caa22b0`）：backend/frontend/tests 共 19 处按新编号更新；指向已删技术债清单（ADR-010/011）的改纯文字。
- 3. **design/ 文档改英文名**（`ea36683`）：architecture.md / ui-ux.md / memory.md。
- 4. **product/ 分层**（`6da8081`）：slogan(使命) / philosophy(原则) / roadmap(计划)。
- 5. **structure/ 模板化重写**（`d81958c`、`6a8dfd2`）：agent.md 及 project/backend/frontend/data/tools 共 6 篇，按 project-docs 的 structure 模板重写，对齐实际代码结构。

### 未提交（待用户 review）

- **docs/index.rst 收敛**：所有 toctree 加 `:hidden:`（主页正文不再渲染目录块/ADR 索引表）；新增「文件导航」表格（ADR/design/product/structure/handoff 六类）；文档状态说明改写（以「修改记录」最新日期为准 + 落后≠失效 + 目录定位速览）；删除副标题「旅行伴侣——基于双引擎 + LLM Agent…」。
- **docs/conf.py**：`exclude_patterns` 调整为 `["_build", ".DS_Store", "feedback", "handoff/archive", "inbox.md"]`，排除内部 feedback、待办 inbox.md 与历史归档 handoff/archive（归档文件仍进 git 跟踪，但不进文档站）。
- **docs/handoff/CURRENT_CODE.md / CURRENT_DOC.md**：补主标题（`# 代码会话交接` / `# 文档会话交接`）+ 内部章节从 `#` 降为 `##`，修复此前 YAML frontmatter 未消费导致正文章节被渲染成 h1 的展示 bug（已 `make docs` 验证 h1 主标题 + h2 章节、frontmatter 不泄漏）。
- **docs/handoff/archive/.gitkeep**（新）：占位文件，写入归档约定说明，让空 archive/ 目录被 git 跟踪（符合 session-handoff 规范：旧 CURRENT_* 移入此处按日期命名）。

### 已修复的其它问题

- project.md 文档索引移除已不存在的 `runbooks/` 目录、移除内部 `feedback/` 目录（feedback 被 .gitignore 忽略、不对外）。

## 决定 / 已知坑

- **docs/runbooks/ 目录已不存在**：旧文档引用 `docs/runbooks/{coding,git,deploy}.md`、`docs/README.md` 均已失效（可能迁移到 .dsh/skills/ 下），不要再依赖它们；本 CURRENT_DOC.md 的下一步目标里也不再引用。
- **archive/ 进 git 需占位文件**：空目录不被 git 跟踪，必须放 `.gitkeep` 或占位文件。`git check-ignore` 对**目录** `docs/handoff/archive/` 的报错是空目录 + CRLF 的 git 误报；对**文件** `.gitkeep` 实测不忽略（EXIT=1）。
- **`autoapi/index` 是运行时生成**：由 conf.py 的 `autoapi_dirs=["../backend"]` 在 `make docs` 时生成，非静态文件；`make docs` 会同时重新生成 docs/openapi.json（conf.py 的 setup 钩子）。
- **Sphinx/myst 对 md 文档**：md 首行若无 `# 主标题`，正文第一个 `#` 会被当作文档级 h1，导致章节错乱——handoff/ 这类含 YAML frontmatter 的文档尤其要注意补主标题。
- **构建警告**：`make docs` 成功，但仍有 ~72 个 warning，全部来自 `docs/autoapi/`（AutoAPI 从后端 docstring 自动生成，既有现象），与手写文档无关，暂不处理。
- **本会话为文档类**：改的是 docs/、.dsh/skills 的 .md 与 .rst；若 .gitignore 想调整 `docs/handoff/archive` 的忽略，需确认当前 `git check-ignore -v` 的误报来源（可能是 CRLF 所致），建议以 `.gitkeep` 方式而非改 .gitignore。

## 下一步目标

1. **等用户 review 未提交改动**（docs/index.rst、docs/conf.py、CURRENT_CODE.md / CURRENT_DOC.md、archive/.gitkeep），确认后由用户决定是否提交到 dev。
2. **若继续文档工作**：可把「文件导航」表格的 ADR 索引（当前以注释保留在 index.rst）按需恢复为正文表格，或保持收敛到 toctree 单一来源（当前做法）。
3. **可选**：`git push origin dev`（当前 dev 领先 origin/dev，且已含 6 笔提交 + 待 review 改动）。
4. 若用户后续要新增/修改文档，沿用 project-docs skill 的 ADR/design/product/structure 模板；交接文档读写走 session-handoff，勿改其规范。