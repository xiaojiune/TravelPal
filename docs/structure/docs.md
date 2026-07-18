# 文档系统介绍

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-07-18 | 初稿 |

## `docs/` 目录结构

| 条目 | 类型 | 说明 |
|------|------|------|
| `ADR/` | 目录 | 架构决策记录（5 份，编号 001-005） |
| `structure/` | 目录 | 项目结构文档（6 份：project/backend/agent/frontend/data/docs） |
| `_build/` | 目录 | Sphinx HTML 构建产物（.gitignore） |
| `_static/` | 目录 | Sphinx 静态资源 |
| `coding.md` | 文件 | 编码规范（P0-P3 四级注释体系） |
| `conf.py` | 文件 | Sphinx 构建配置 |
| `deploy.md` | 文件 | 部署指引（Docker 上线） |
| `index.rst` | 文件 | Sphinx 文档首页/导航 |
| `openapi.json` | 文件 | OpenAPI 规范（Sphinx 构建自动生成） |
| `产品路线图.md` | 文件 | 产品四阶段规划 |

## 文档分工

| 目的 | 文档 |
|------|------|
| 项目全局概览 | [`project.md`](project.md) |
| 后端架构详解 | [`backend.md`](backend.md) |
| Agent 层详解 | [`agent.md`](agent.md) |
| 前端架构详解 | [`frontend.md`](frontend.md) |
| 全链路数据字典 | [`data.md`](data.md) |
| 架构决策记录 | `ADR/001.md` ~ `ADR/005.md` |
| 编码规范 | `../coding.md` |
| 产品路线图 | `../产品路线图.md` |
| 部署运维 | `../deploy.md` |

## Sphinx 构建

```bash
make docs            # 生成 HTML 文档 → docs/_build/
make docs-serve      # 本地预览
```

入口文件为 `index.rst`，自动从 `ADR/` 和 `structure/` 引入导航。
