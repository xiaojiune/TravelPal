---
name: travelpal-coding
description: TravelPal 编码规范：四级注释体系、docstring 格式、接口清单、数据模型与 VNS 引擎写法约定。
whenToUse: 写/改/重构代码、补注释或 docstring、改 API 签名或 schemas、加数据模型、调 VNS 引擎参数时使用；不确定注释几级、接口怎么列时尤其要用。
allowed-tools: read, edit, write, grep, glob, bash
---

# TravelPal 编码规范

> 覆盖项目前后端 + VNS 引擎的编码规范。共同约定放在本 SKILL.md（脚本每次加载都拿到），域规范放 `references/` 按需加载。

## 一、注释四级体系（前后端统一）

| 等级 | 特征 | 目标 |
|------|------|------|
| P0 不合格 | 无注释 / 函数名复述 / 参数缺失 | 不允许 |
| P1 合格 | 一句话功能 + 完整 Args/Returns | 底线要求 |
| P2 优秀 | 设计意图 + 边界约定 + 异常行为 | 追求目标 |
| P3 详尽 | 逐行解释算法与数学推导 | 仅核心算法模块 |

- P0 绝对不允许。前后端各自 Lx 分级见对应 reference。

## 二、触发导航（按任务域加载）

- **写/改常规后端代码**（API、schemas、数据模型、服务）→ 加载 `references/backend.md`
- **写/改前端**（Vue 组件、路由、store）→ 加载 `references/frontend.md`
- **改 VNS / 优化引擎**（元启发式算法、适应度、参数）→ 加载 `references/engine.md`

## 三、通用硬约束（不随域变）

- **中文**：推理、对话、注释、docstring 用中文；代码、变量名、API 字段用英文。
- **类型注解**：公开 API 必须完整标注；数组统一 `np.ndarray`。
- **导入顺序**：标准库 → 第三方 → 项目内部，组间空行；函数内 import 注释原因。
- **魔术数字**：不求硬编码，用常量/枚举命名。
- **单函数长度**：软约束 80 行，核心算法可到 120 行。

## 四、与其它 skill 的关系

- 测试规范（何时跑、划范围）→ `travelpal-testing`（本 skill 只管"怎么写代码"，不管"何时测"）。
- 描述性/历史性内容（现状评估、ADR 引用）已从本 skill 剔除，只留可执行规范。
