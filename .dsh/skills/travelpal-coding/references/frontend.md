# 前端编码规范（TravelPal frontend）

> 写/改前端（Vue 组件、路由、store、API 服务）时的规范。

## 语法与结构

- **`<script setup>` + Composition API**。状态用 `ref()`（不用 `reactive()`），派生值用 `computed()`。
- **Composition API 结构（`<script setup>` 内按序）**：import → store/router → Props/Emits → 响应式状态 → 计算属性 → 生命周期 → 事件/方法 → watch（放最后）。
- **父子通信**：用回调函数 prop（项目约定，不用 `defineEmits`）。

## 命名风格

- 组件文件：`PascalCase.vue`（`SchedulePanel.vue`）；页面文件：`PascalCase.vue`（`HomePage.vue`）。
- 服务/工具文件：`camelCase.ts`（`api.ts`）。目录全小写（`components/`、`pages/`、`stores/`）。
- Pinia store：`use` 前缀 + `Store` 后缀（`usePlanStore`）。

## Props / 接口清单

- Props 用 TypeScript 泛型定义接口，同时声明 `type` 和 `default`（`withDefaults`）。
- **组件级清单**：组件定义处用注释块声明公开 API。
- **路由**：集中定义在 `router/index.ts`，页面全部懒加载。
- **Store 清单**：Pinia store 通过 `return` 显式暴露的接口即公开 API。

## API 服务

- 用 axios 实例，`baseURL: '/api'`，在 service 层解包 `response.data`。
- 组件 Props 直接绑定：用 `v-bind` 逐个传递，不用对象展开。

## 注释优先级分层

- **L0** 核心复杂组件（AmapMap.vue、ChatMessage.vue）：P2~P3，JSDoc + 行内 Why + 设计意图。
- **L1** 管道/展示组件（SchedulePanel.vue、HomePage.vue）：P1~P2，JSDoc + 关键逻辑 Why。
- **L2** 页面容器 / store / 工具（SuggestPage.vue、stores/*.ts）：P1，组件职责 + 行内 Why。

## 组件粒度与逻辑复用

- 组件根元素为 class 挂钩时，模板保持可读，不混入逻辑。
- 复用抽组件，避免大组件堆逻辑。

## 反模式（不推荐）

- 不用 `reactive()`（用 `ref()`）。
- 不用 `defineEmits`（回调 prop）。
- Props 不用对象展开传递。
