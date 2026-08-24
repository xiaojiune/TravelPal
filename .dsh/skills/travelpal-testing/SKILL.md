---
name: travelpal-testing
description: TravelPal 测试规范。涉及跑测试、写测试、判断测试何时该跑、确定测试范围时使用。它规定何时跑测试（用户要求/改测试/验证功能）、如何划改动范围（git status 定本次改动、只跑对应模块）、依赖外部环境的测试要先探测端口、新增依赖按生产/开发分组、以及项目的测试风格（三档数据 fixture、纯函数测试、slow marker）。把 AGENTS.md 里的测试边界与项目实际测试约定固化于此。
whenToUse: 用户要跑测试、写/改测试、判断某个改动是否需要测试、排测试失败、或涉及仓库集/数据 fixture/外部环境测试时使用。用户提到 pytest、conftest、fixture、测试范围、环境探测时尤其要用。
allowed-tools: read, edit, write, grep, glob, bash
---

# TravelPal 测试规范

> 覆盖"何时跑测试、怎么写测试、测试范围与外部环境判断"。从项目现状（conftest.py、pytest.ini、AGENTS.md 边界）提炼，可直接执行。

## 一、何时跑测试（哪个场景才跑）

仅在以下情况执行测试：
1. 用户**明确要求**运行测试
2. **修改了测试代码**本身需要验证
3. 用户**要求验证某功能**是否正常

**执行前先 `git status`** 确定本次改动范围，**只跑本次改动对应模块的测试**，不跑无关测试。

## 二、外部环境测试（边界判断）

- 执行**依赖外部环境**的操作前（PostgreSQL/Redis/Celery worker 的端到端验证、前后端联调），**先探测端口**（如 5432/6379）。
- **环境不可用 → 终止操作并提醒用户先启动**，不擅自跳过或降级执行。
- **纯单元测试**（引擎/纯函数，不依赖外部服务）不受此限，可随时跑。

## 三、依赖分组

新增依赖按「生产镜像或部署流程是否需要它」判定：
- **production**：生产运行/部署需要（FastAPI/Celery/alembic/redis）
- **development**：纯开发工具（pytest/ruff/pyright）

判定标准：部署（`docker compose run --rm backend ...`）或 `poetry export`（仅导出生产组）是否执行它——是则 production，否则 development。

## 四、测试风格（项目现状）

- **数据集 fixture**：`tests/conftest.py` 覆盖三种规模：
  - `n20_dataset`（小，`n20w20` 实例1）
  - `n40_dataset`（中，`n40w20` 实例1）
  - `n60_dataset`（中偏大，`n60w60` 实例3）
  - `any_dataset`：参数化 fixture，可批量跑多种数据集。
  - `base_adjust_plan`：n20 基础调整计划，注意 `dataset_loader` 缺 `original_tw`，真实 run_planning 会构建。
- **测试类型**：`tests/` 分 `test_agent` / `test_contract` / `test_engine` 等模块。
- **markers**（pytest.ini）：`slow` 标记大规模数据集测试（可能耗时较长）。

## 五、写测试要点

- 测试引擎/纯函数用上述 fixture 加载数据集，断言成本结构/违规数等可验证结果。
- 外部依赖的测试要显式探测环境，不可静默跳过。
- 遵循 coding 规范里"只跑本次改动对应模块"的边界，控制测试范围。
