---
task: "P1 收尾(想法21-B 索引 / 想法14 POI缓存 / 想法3 Celery可靠性) + Release 自动发布链路改造 + 想法7 可观测性落地(Prometheus+Grafana) + 想法22 restart/健康检查 + 模型换多模态"
status: "done"
date: "2026-09-12"
version: "0.2.0"
range: "2026-08-31..2026-09-12"
git: "e6e94c0..7e1deec"
---
# 代码会话交接

## 上一段进行到哪

本会话完成 **P1 全部剩余项 + P2 两项落地 + 发布链路改造**，已提交并推送 `origin/dev`；工作区干净。

### 入口动作：交接核实
- 读取上一档 CURRENT_CODE.md 发现**已过期**（档称"dev 领先 8 commit 未推"，实际早已推送且发布了 v0.2.0）。教训：交接档是参考，先 `git log/status` 核实现状再行动。

### 发布链路改造（Release 移到流程最后）
- `6b92f4a`：`release.yml` 从 `on: push tags` 改为 `workflow_run` 监听 **Deploy 成功**；版本号读 `pyproject.toml` 的 version，自动打 tag 指向部署的 commit（`workflow_run.head_sha`）；`if` 同时要求 `conclusion=='success'` **且** `event=='push'`（排除 PR 触发的 CI）。
- `8df18ee`（另一会话）：git 发布描述同步为自动链路（CI+Docs→Deploy→Release）。
- `e157bb6`：同步 main 到 dev（Merge）。

### P1 收尾
- `54d8d88`（**想法21-B 索引**）：`plan_tasks` 加 `(user_id, created_at)` 复合 + `created_at` 单列；`share_records` 加 `created_at` 单列；**删除冗余** `ix_plan_tasks_user_id`；迁移 `6f2c9100d4b5`。
- `c516675`（**想法14 POI 缓存**）：新增 `infra/external/amap/poi_cache.py` **单层缓存**（`tp:poi:{city}:{name_fp}`，TTL 24h，Redis 降级）+ 修复**酒店重复 LLM 解析**（酒店跳过解析，直接 0/1440）+ **统一 agent 工具与 HTTP 端点逻辑**（共用同一缓存，酒店判定必须一致）。
- `77d1e69`（**想法3 Celery 可靠性**）：死信队列（`plan` 队列配 `x-dead-letter-exchange` → `plan.dead`）+ `autoretry_for=(TransientError,)` 指数退避 max 3 + **终态幂等**（重投时 done/failed/canceled 直接跳过）+ `_is_transient` 区分连接抖动/业务错误。

### P2 落地（想法7 + 想法22）
- `d0289b3`（**想法7 可观测性**）：新增 `docker/prometheus.yml`（抓 nginx + Basic Auth）+ `docker/grafana/`（数据源 uid=prometheus + dashboard provider + `travelpal-overview` 看板）+ compose 加 prometheus/grafana 服务 + `nginx.conf` 加 `/grafana/` 子路径反代 + AdminPage 加"监控看板"跳转按钮。
- `d0db670` / `3ef1859`：密码注入——`PROMETHEUS_BASIC_PASS` 注入 prometheus 容器、`GF_SECURITY_ADMIN_PASSWORD` 注入 grafana 容器；`.env.example` 补充两项。
- `aaccc89`（**想法22**）：全 8 服务加 `restart: unless-stopped`；backend 新增 `GET /api/health` + redis/worker/nginx healthcheck。

### 其它
- `55201b2`：`LLM_MODEL` 改用多模态 `deepseek-v4-flash-vision-exp`（`.env` + `.env.example`）。
- `2a0bfd0`：`.dockerignore` 补 `.idea/`、`.coverage`、`coverage.xml`、`.ruff_cache/`、`tests/`、`raw_data/`。
- **服务器侧（手动，无 commit）**：建 `/etc/nginx/.htpasswd`（metrics 用户）+ 服务器 `.env` 写 `PROMETHEUS_BASIC_PASS`；服务器无 `htpasswd`，已装 `apache2-utils`。
- ⚠️ **服务器代码尚未拉取本会话改动**（仍停在 `f00cb83`），prometheus/grafana 容器未起、`/grafana/` 暂不可访问。

## 决定 / 已知坑（本会话）

- **Release 自动链路**：Release 由 **Deploy 成功**触发（不再 `push tags`）；版本号读 `pyproject.toml` 的 `version`，`target_commitish` 用被部署的 `head_sha`；正文读 `docs/releases/v<version>.md`。**发布前必须 bump pyproject 版本**，否则重复打同一 tag。
- **索引设计**：`plan_tasks (user_id, created_at)` 复合服务**用户任务面板**；`created_at` 单列服务 **admin 全量列表**（无 user 过滤时复合索引不命中）；`share_records` 只建 `created_at` 单列（**全站分享站无 user 过滤**）；**不做 JSONB GIN**（result/request_params 从无内容筛选查询）。
- **POI 缓存单层、不拆两层**：`biz_hours`(高德) 与 `tw_start/end`(LLM解析) 同刻同源、解析结果是高德响应的纯派生，拆 L1/L2 只会引入"L1命中L2过期"复杂度；键为规范化名称 sha1 指纹；**酒店跳过 LLM**（全天 0/1440）；agent 工具与 HTTP 端点**共用同一缓存，酒店判定逻辑必须一致**。
- **Celery 可靠性**：死信队列 `plan.dead`；`autoretry_for=(TransientError,)` 仅重试瞬时错误；`_is_transient` 判连接/DB 抖动（SQLAlchemy DBAPIError/DisconnectionError/OperationalError + ConnectionError/TimeoutError）；**终态幂等**（重投时 status ∈ done/failed/canceled 直接 return）；`task_reject_on_worker_lost=True`。
- **可观测性**：`/api/metrics` 经 nginx **Basic Auth**（`.htpasswd` 的 metrics 用户）；**Prometheus 抓 `nginx`（非直连 backend）**；Grafana 子路径 `/grafana/`（需 `GF_SERVER_ROOT_URL` + `GF_SERVER_SERVE_FROM_SUB_PATH=true`）。
- **密码注入两层展开**：`.env` → compose 展开 → 容器环境变量 → **Prometheus 启动时填 `prometheus.yml` 的 `${PROMETHEUS_BASIC_PASS}`**。`PROMETHEUS_BASIC_PASS` 填**明文**（客户端凭证），`/etc/nginx/.htpasswd` 存该明文的 **hash**（服务端校验）。
- **Grafana 密码**：`GF_SECURITY_ADMIN_PASSWORD` 仅**首次启动消费一次**；首登后**强制改密，新密码只写 Grafana DB（`grafana_data` volume），不回写 `.env`**；删 volume 才会重新应用初始密码。
- **健康检查**：backend `GET /api/health` 只检**进程存活**（不查 DB/Redis，避免外部抖动误判 down）；worker 用 `pgrep -f celery`；nginx 用 `wget` 本地探测；**lavinmq 未加强制 healthcheck**（探针不确定，避免误杀）。
- **模型多模态**：`LLM_MODEL=deepseek-v4-flash-vision-exp`（支持视觉）；但 `domain/llm_service.py` 的 `messages` 仍是**纯文本约定**，图片 content 通道未定义。
- **服务器信息**：部署目录 `~/TravelPal`；SSH 用户/密钥见本地 `.env.local`（不进 git，勿写入本档）；注意服务器原有一个 `/etc/nginx/htpasswd` **目录**，项目用的是 `/etc/nginx/.htpasswd` **文件**。

## 评估结论（本会话，未动代码）

- **想法19（NP-hard/QPS）不做**：预置热门城市距离矩阵**不可行**（矩阵依赖用户 POI 组合，命中率趋零）；多级缓存当前无 QPS 压力。
- **想法23（前端虚拟滚动）不做**：`SchedulePanel` 是几十行原生 table、`HomePage` 景点卡是**手风琴单卡展开**（重组件只渲染 1 个），均未到需虚拟化的量级；实际也未遇到卡顿。
- **LLM-as-Judge 暂缓**：LLM 调用点均已有硬约束/兜底（营业时间解析有 0-1440 校验、停留时间有 fallback、工具调用有 error 回填重调），Judge 收益不抵成本。
- **想法27（外部 UGC / 多模态分享）值得做但留待后续**：模型前提已具备，需一次**跨层迭代**（LLMService 协议扩多模态 + 编排 + 前端上传入口 + 图片→结构化卡片）。

## 下一步目标

1. **服务器部署（最优先）**：服务器仍停在 `f00cb83`，需 `git pull` + `docker compose up -d`，让 Celery 可靠性 / 监控编排（`/grafana/`）/ 健康检查 / 多模态模型 生效。部署后首访 `/grafana/` 用 `admin/admin` 登录并改密（存 Grafana DB）。
2. **发布 v0.3.0（如需要）**：先 bump `pyproject.toml` 的 version 并补 `docs/releases/v<version>.md`，合入 main 后自动走 CI→Deploy→Release（自动打 tag）。
3. **想法27（多模态 UGC）**：若启动先出方案（LLMService 协议扩展 + 前端图片入口 + 图片→旅行卡片，**只进用户私有会话、不进公共库**）。
4. **可选**：`infra/auth/postgres_conversation_store.py` 拆到 `infra/conversations/`（语义更纯）。
