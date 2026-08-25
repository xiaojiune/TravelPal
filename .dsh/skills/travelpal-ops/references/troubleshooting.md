# 排障规范（TravelPal troubleshooting）

> 常见故障速查，按「症状 → 排查 → 解决」组织。未能覆盖时，见 ARCHITECTURE.md 定位问题模块。

## 一、容器起不来

- **排查**：`docker compose config`（语法）、`docker compose ps`（看 Exited/Restarting）、`docker compose logs postgres/redis/backend`、`ss -lntp | grep -E '5432|6379|8000|80|443'`。
- **解决**：
  - 5432/6379 端口被占用 → 停占用进程或改映射端口
  - 8000 被本地后端占用 → 先停 `make serve` 再起容器
  - `.env` 缺失 → `cp .env.example .env` 补全 Key
  - 镜像构建失败 → `docker compose build --no-cache backend`

## 二、规划任务 failed

- **排查**：`GET /api/tasks/{id}` 看 error 文案；`docker compose logs worker` 看 worker 栈；`check plan_tasks` 表记录。
- **解决**：
  - `缺少字段 ['tw_start','tw_end','stay']` → 调用方先 poi_lookup 获取营业时间再提交
  - `驾车路径查询失败` → 高德配额/限流；任务内建 3 次重试，耗尽后失败
  - 其它 RuntimeError → 看 worker 完整栈，引擎 bug 按 ADR-010 技术债跟踪

## 三、API Key 失效

- **排查**：`curl http://localhost:8000/api/metrics` 看调用计数；日志搜 `401`/`INVALID_USER_KEY`/`QUOTA`；检查服务器 `.env` 4 个 Key。
- **解决**：
  - 高德配额耗尽 → 提升配额或降 worker concurrency
  - Key 类型用错 → Web Key（AMAP_API_KEY）配后端；JS Key（AMAP_JS_KEY）配前端地图
  - DeepSeek 401/余额不足 → 检查 LLM_API_KEY/LLM_BASE_URL，充值或换 Key
  - 改 .env 未生效 → `docker compose restart backend worker`

## 四、/api/metrics 无数据

- **排查**：`curl -u <用户>:<密码> http://localhost:8000/api/metrics`（Nginx Basic Auth）；确认 `PROMETHEUS_MULTIPROC_DIR` 已配置（backend/worker 同目录）；`ls -la /tmp/travelpal_metrics/` 看 mmap 残留。
- **解决**：
  - 未设 PROMETHEUS_MULTIPROC_DIR → .env 配置并在 compose 注入，两服务同 volume
  - 指标只在 worker 累计 → 确认共享目录
  - 死 mmap → `rm -f /tmp/travelpal_metrics/*.db`
  - Nginx 500 → `htpasswd -c /etc/nginx/htpasswd <用户>` 创建鉴权文件

## 五、数据库连接 / Alembic 迁移异常

- **排查**：`docker compose ps postgres`；`.venv/bin/alembic current` vs `alembic heads`；核对 `DATABASE_URL`。
- **解决**：
  - 数据库未启动 → `make dc-up`（本地）/ 确认 postgres healthy（部署）
  - 迁移未应用 → `make migrate`（= alembic upgrade head）；生产已自动执行
  - 建表与迁移冲突 → 全新环境直接跑迁移，勿同时用 `init_db()` 建表
  - 连接池跨 loop 报错 → 任务内每轮 `asyncio.new_event_loop()` + `engine.dispose()`，重启 worker 重建

## 六、本地开发三终端核对

- **排查**：三终端是否在跑（`make dc-up` / `make serve` / `make celery`）；任务 pending → worker 未起或未连 Redis；前端失败 → 后端未起或 Vite proxy 未配。
- **解决**：
  - 基础设施 `make dc-up` → `docker compose ps` 见 postgres/redis healthy
  - 后端 `make serve` → `curl :8000/docs` 200
  - worker `make celery` → 终端见 `[INFO] celery@... ready`

> worker 是独立进程，改 `tasks/` 后需重启 worker 生效（不热重载）。
