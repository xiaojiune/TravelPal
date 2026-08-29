---
name: travelpal-ops
description: TravelPal 运维与排障规范：分部署（deploy）与排障（troubleshooting）两类。部署、排障、看日志时使用。
whenToUse:
  - 用户明确指令：部署、配置服务器、看日志、重启服务、配域名或 HTTPS
  - 特定场景：排查故障（容器起不来、任务失败、API key 失效、指标无数据、DB 迁移异常、本地联调）
  - 关键词提及：部署、deploy、日志、重启、域名、HTTPS、排障、故障
  - 不触发：纯编码/文档/测试任务，不涉部署或排障
allowed-tools: read, edit, write, grep, glob, bash
---

# TravelPal 运维与排障

> 覆盖部署 + 故障排查两块。共同约定在 SKILL.md，具体部署/排障细节在 `references/` 按需加载。部署脚本在 `scripts/deploy.sh`。

## 一、触发导航（按需加载）

- **部署项目**（服务器初始化、Docker、环境变量、域名/HTTPS）→ 加载 `references/deploy.md`
- **排障**（容器/任务/Key/指标/DB/本地联调）→ 加载 `references/troubleshooting.md`

## 二、部署脚本

`scripts/deploy.sh` 提供一键部署：克隆/拉取 → 配置 .env → `docker compose up -d --build` → 验证 API。服务器已部署好时，主要用它做**更新到最新版本**（`git pull` + `docker compose up -d --build`）。

## 三、通用运维硬约束

- **环境探测**：执行依赖外部环境的操作前先探测端口（5432/6379/8000），不可用则提醒先启动，不擅自降级。
- **API Key**：服务器 `.env` 需配置 4 个 Key（高德 Web/JS、LLM），改了要重启 backend/worker 容器才生效。
- **Nginx + Basic Auth**：`/api/metrics` 等接口经 Nginx Basic Auth 保护。

## 四、关键命令速查

| 操作 | 命令 |
|------|------|
| 看日志 | `docker compose logs -f --tail=100 backend` |
| 重启服务 | `docker compose restart backend` |
| 更新版本 | `git pull && docker compose up -d --build` |
| 迁移 | `make migrate`（= alembic upgrade head）|
| 基础设施 | `make dc-up`（postgres+redis）|

## 五、与其它 skill 的关系

- 版本发布/tag → `travelpal-git-release`（git 侧）；本 skill 是**服务器/运维侧**，两者互补。
- 编码/测试规范 → `travelpal-coding` / `travelpal-testing`。
