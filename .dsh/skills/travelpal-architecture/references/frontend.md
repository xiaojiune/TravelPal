# 前端目录拆分与逻辑抽取（做法）

> 一行深引用，本文件供 SKILL.md 按需加载。前端目录职责边界 + 拆分/抽取方法论 + 类型单一来源检查，不涉代码风格。

## 目录职责边界

| 目录 | 职责 | 可放 | 不可放 |
|---|---|---|---|
| `pages/` | 路由页面，薄壳 | 页面组装、读取 store/composable、local 状态 | 业务逻辑、直接 axios、重复数据格式化 |
| `components/` | 界面组件 | 带 props/emits 的可复用 UI | store 依赖、接口调用（组件只 emit 事件） |
| `composables/` | 可复用组合函数 | 跨组件/跨页复用的逻辑 | 单处使用、纯静态函数 |
| `stores/` | Pinia 全局状态 | 跨页共享状态（plan、user、credits） | 仅单页使用、纯函数计算 |
| `services/` | 后端接口统一层 | axios 实例、类型化接口调用（api.ts） | 页面/组件里的 axios.get |
| `utils/` | 通用纯函数（无状态） | 时间格式化、纯计算 | 依赖组件生命周期、store |
| `router/` | 路由表（懒加载） | 页面路由映射 | 业务逻辑 |
| `api/types.generated.ts` | OpenAPI 生成类型（唯一来源） | 接口类型 | 手写重复定义 |

**核心**：页面薄、逻辑进 composable、共享状态集中 store、接口收敛 services。数据流单向清晰（`ChatStream emit → AgentPanel 转 store → PendingPanel 读 store`）。

## 拆分方法论（对应 SKILL.md 原则六）

**文件长不是拆分的理由，拆分看"变化是否独立"。**

判断一张表 / 一个长文件该不该拆，问三个问题：

1. **改动是否独立？** 改 A 块不动 B 块 → 可拆；每改都牵连 → 硬拆制造跨文件耦合。
2. **是否引入新职责？** 文件里混了两种职责（如"数据获取 + 展示"）→ 拆；单一职责但长 → 不拆。
3. **是否有多个复用户？** 只有一页用 → 别为了"看起来清爽"拆；多页复用 → 拆成 composable/component。

> 例：`routes.py` 415 行但内聚，不该拆（那是"长但单一职责"）。而一个组件同时做 fetch + 渲染 + 编辑状态 → 该拆（多职责）。

## 逻辑抽取方法论（对应 SKILL.md 原则三/七）

**同一逻辑只有一处定义；第 3 次出现才抽象。**

- **1 次**：内联，别抽象。
- **2 次**：可忍，标注"出现第二次"，暂不抽取。
- **3 次**：提公共模块（composable / util / 公共 CSS class）。

抽取时机判断：是"真重复"还是"形似神不同"？形似的刻意保留，真正的重复才提。

**抽取去哪个目录**：
- 跨组件/跨页复用 → `composables/`
- 无状态纯函数 → `utils/`
- 后端接口调用 → `services/api.ts`（组件里绝不直接 `axios.get`）
- 纯样式重复 → 公共 CSS class（如 `.tp-card`）

## 类型单一来源检查（对应 SKILL.md 原则九）

**接口/全局状态/类型结构值得单一来源；纯实现细节不值得。**

- `services/api.ts` 里**不要重复手写** `types.generated.ts` 已有的类型（TaskDetail/HistorySummary 等）→ 直接 import generated 类型。
- 别用 `& { ... }` 交集重定义生成类型已包含的字段（会掩盖 OpenAPI 更新）。
- 前端类型与后端 `typedefs.py` / OpenAPI 双处手工同步 = 漂移风险（ADR-011 #1）→ 走 OpenAPI 单一来源（`gen:api` 已入 check）。

## 放错层的信号（前端）

- 组件里直接 `axios.get('/xxx')` → 改走 `services/api.ts`。
- 同一段逻辑在多页复制 → 抽到 `composables/` 或 `utils/`。
- 单页才用的状态塞进全局 store → 提回页面/local，或拆 composable（如 suggest 缓存 → `useSuggestCache`）。
- 一个函数接受双形状参数靠运行时判断 → 拆成两个明确函数。
- 死代码 / 失效样式 / 零引用 token → 必清（原则四"全是精华"）。

## 案例：新增一个跨页复用的数据逻辑

1. 先探：现有结构里有没有类似逻辑（composables/ 已有 usePoiSearch/useTaskPolling...）。
2. 判断：是否多页复用？是 → 新建 `composables/useXxx.ts`；仅一页 → 放页面。
3. 检查重复：是否已出现第二次？是 → 抽取；否 → 暂缓（Rule of Three）。
4. 类型：用 generated 类型，不手写重复声明。
