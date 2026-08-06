# Git 工作流

## 修改记录

| 日期 | 变更 |
|------|------|
| 2026-07-19 | 初始创建 |

## 分支说明

| 分支 | 指向 | 说明 |
|------|------|------|
| `main` | `origin/main` | 发布分支，只从 GitHub PR 合并 |
| `dev` | `origin/dev` | 开发分支，所有工作在此提交 |

> 当前项目处于早期开发阶段，所有开发工作直接在 `dev` 分支进行，不设特性分支。

## 分支策略

```
本地 dev（开发）  →  git commit →  git push origin dev
                                        ↓
                                    origin/dev
                                        ↓
                                  GitHub PR → origin/main
                                        ↓
                                  本地 main ← git pull origin main
                                        ↓
                                  本地 dev  ← git merge main
```

## Commit 规范

格式：`<type>: <简短描述>`

- type 使用小写英文：`feat` / `fix` / `docs` / `chore` / `refactor` / `test`
- 描述使用中文，简洁说明改了什么

示例：

```
feat: 增加 POI 查询 Function Calling
fix: 修复高德地图 IP 白名单配置失效问题
docs: README 重构——核心功能 + Docker 快速开始 + 技术栈
chore: Makefile 增强——新增 5 命令 + help + 全命令注释
refactor: tools.py 拆分为 tools/ 子包
test: 添加 _classify_poi / _tokenize 纯函数单元测试
```

## PR 规范

- PR 标题格式同 Commit 规范
- PR 描述包含：改了什么、为什么改、如何验证
- 合并方式：统一使用 **Squash and merge**

## 外部贡献（Fork 工作流）

1. Fork 本仓库到你自己的 GitHub 账号
2. 在 Fork 的仓库中创建分支并提交改动
3. 向本仓库的 `dev` 分支发起 PR
4. PR 通过 CI 检查后由维护者合并