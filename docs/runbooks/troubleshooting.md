# 故障排查手册

面向开发与运维的常见故障速查。每个故障按「症状 → 排查步骤 → 解决」组织。
如未能覆盖，见 [ARCHITECTURE.md](../../ARCHITECTURE.md) 了解分层后定位问题模块。

## 修改记录

| 日期 | 变更 | 动机 |
|------|------|------|
| 2026-08-06 | 初始创建 | 补齐运维文档，沉淀实际踩坑的排查路径 |

## 一、容器起不来

**症状**：`make dc-up` / `docker compose up -d` 报错或服务一直 restart。

**排查步骤**：

1. `docker compose config` 验证 compose 文件语法与服务定义
2. `docker compose ps` 查看哪些服务异常（Exited/Restarting）
3. `docker compose logs postgres` / `logs redis` / `logs backend` 看具体报错
4. 端口占用：`ss -lntp | grep -E '5432|6379|8000|80|443'`

**解决**：

| 原因 | 处理 |
|------|------|
| 5432/6379 端口被宿主机进程占用 | 停掉占用进程或改 docker-compose 映射端口 |
| 8000 被本地后端占用 | 开发时先停 `make serve` 再起容器，或直接只用容器跑基础设施 |
| `.env` 缺失 | `cp .env.example .env` 后补全 API Key（见 [deploy.md](./deploy.md)） |
| 镜像构建失败 | `docker compose build --no-cache backend` 重试，注意网络镜像源配置 |

## 二、规划任务 failed

**症状**：前端轮询任务最终 `status=failed`，或 `GET /api/tasks/{id}` 返回 error 字段。

**排查步骤**：

1. `GET /api/tasks/{id}` 的 error 文案定位失败类型
2. `docker compose logs worker`（或本地 `make celery` 终端）看 worker 侧异常栈
3. 确认 plan_tasks 表记录：`select status, error, request_params from plan_tasks order by created_at desc limit 5;`

**解决**：

| error 文案 | 含义 | 处理 |
|-----------|------|------|
| `缺少字段 ['tw_start', 'tw_end', 'stay']` | 景点未先经 poi_lookup 获取营业时间 | 调用方先查询 POI 再提交（get_plan 已强制校验，不填默认值） |
| `驾车路径查询失败...` | 高德驾车 API 拉取失败（配额/参数） | 检查高德 Key 配额与限流；网络重试由任务内建 3 次，耗尽后整任务失败 |
| 其它 RuntimeError | 引擎/参数内部错误 | 看 worker 完整栈，属引擎 bug 按 [ADR-010](./../ADR/010.md) 技术债跟踪 |

## 三、API Key 失效

**症状**：POI 查询全部失败、对话无回复、规划报高德/LLM 错误。

**排查步骤**：

1. `curl http://localhost:8000/api/metrics` 看 `llm_calls_total` / `driving_calls_total` 计数是否增长
2. 后端日志中搜 `401` / `INVALID_USER_KEY` / `QUOTA` 等关键词
3. 检查服务器 `.env` 中 4 个 Key 是否正确（高德 Web/JS、DeepSeek）

**解决**：

| 原因 | 处理 |
|------|------|
| 高德配额耗尽（QPS 超限） | 提升配额或降低并发（worker concurrency） |
| 高德 Key 类型用错 | Web 服务 Key（AMAP_API_KEY）用于后端，JS Key（AMAP_JS_KEY）用于前端地图 |
| DeepSeek 401/余额不足 | 检查 `LLM_API_KEY` / `LLM_BASE_URL`，充值或更换 Key |
| 修改 .env 后未生效 | 重启 backend/worker 容器：`docker compose restart backend worker` |

## 四、/api/metrics 无数据

**症状**：访问 `/api/metrics` 返回空指标或缺少某类指标（如 driving/llm 全为 0）。

**排查步骤**：

1. 确认能访问：`curl -u <用户>:<密码> http://localhost:8000/api/metrics`（Nginx 有 Basic Auth）
2. 确认 `PROMETHEUS_MULTIPROC_DIR` 已配置（后端与 worker 需指向同一目录）
3. 检查 mmap 残留：`ls -la /tmp/travelpal_metrics/` 是否有 `counter_*.db` / `histogram_*.db`

**解决**：

| 原因 | 处理 |
|------|------|
| `PROMETHEUS_MULTIPROC_DIR` 未设置 | 在 .env 配置并在 docker-compose 注入（backend/worker 同一目录） |
| 指标只在 worker 进程累计 | 多进程聚合依赖共享目录，确认两服务挂同一 volume |
| 死 mmap 文件 | `prometheus_client` collect 会自动跳过，可定期 `rm -f /tmp/travelpal_metrics/*.db` 清理 |
| 部署后 Nginx 报 500 | `htpasswd -c /etc/nginx/htpasswd <用户>` 创建鉴权文件（nginx 挂载它） |

## 五、数据库连接 / Alembic 迁移异常

**症状**：启动报 `could not connect to server`、迁移命令报错、表结构不一致。

**排查步骤**：

1. `docker compose ps postgres` 确认数据库健康
2. `.venv/bin/alembic current` 查看当前版本；`alembic heads` 查看最新迁移
3. 连接串核对：`DATABASE_URL=postgresql+asyncpg://travelpal:travelpal123@localhost:5432/travelpal`

**解决**：

| 原因 | 处理 |
|------|------|
| 数据库未启动 | `make dc-up`（本地）；部署环境确认 postgres 容器 healthy |
| 迁移未应用 | `make migrate`（= alembic upgrade head）；生产 deploy.yml 已自动执行 |
| 手工建表与迁移冲突 | 全新环境直接跑迁移，勿同时用 `init_db()` 建表（见 [deploy.md](./deploy.md)） |
| 连接池跨 loop 报错 | 任务内每轮 `asyncio.new_event_loop()` + `engine.dispose()`，重启 worker 后自动重建 |

## 六、本地开发三终端流程核对

**症状**：本地联调时接口无响应、任务一直 pending、前端报跨域。

**排查步骤**：

1. 三个终端是否都在运行：`make dc-up`（postgres+redis）、`make serve`（后端）、`make celery`（worker）
2. 任务 pending 不流转 → worker 未起或未连 Redis
3. 前端请求失败 → 后端未起或 Vite proxy 未配置

**解决**：

| 终端 | 命令 | 验证 |
|------|------|------|
| 基础设施 | `make dc-up` | `docker compose ps` 看到 postgres/redis healthy |
| 后端 | `make serve` | `curl http://localhost:8000/docs` 200 |
| Celery worker | `make celery` | 终端出现 `[INFO] celery@... ready`，任务开始流转 |

> 注意：worker 是独立进程，修改 `tasks/` 相关代码后需重启 worker 生效（不热重载）。
