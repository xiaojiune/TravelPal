# 运维与规范手册

`docs/runbooks/` 目录的索引。汇集开发与运维的规范类和操作类文档，
覆盖从编码、分支到部署、故障排查的完整工作流。

## 修改记录

| 日期 | 变更 | 动机 |
|------|------|------|
| 2026-08-06 | 初始创建（收录 coding/deploy/git） | 收拢 docs/ 根目录散落的规范文档，runbooks/ 成为「规范 + 手册」集合 |
| 2026-08-25 | 编码规范与 Git 规范 skill 化（coding.md/git.md 移除） | 规范转为按需加载的 skill，runbooks/ 保留 deploy/troubleshooting |

## 本目录索引

| 文档 | 覆盖 | 场景 |
|------|------|------|
| 编码规范 | `travelpal-coding` skill | 写代码前加载 |
| Git/版本发布 | `travelpal-git-release` skill | 发布 / 同步前加载 |
| 运维与排障 | `travelpal-ops` skill | 部署 / 排障前加载 |
| 测试规范 | `travelpal-testing` skill | 跑测试前加载 |

## 维护契约

- 规范类文档（coding/git）变更时同步检查各 ADR 的交叉引用与 `AGENTS.md`
- 部署/排查文档（deploy/troubleshooting）变更时同步检查 `docs/index.rst`（导航唯一事实源）
- 本目录文件增删时更新 `docs/index.rst` 文档导航
