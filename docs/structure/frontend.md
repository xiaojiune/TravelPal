# 前端结构

## 目录结构

```
frontend/
├── index.html                  # SPA 入口
├── vite.config.js              # Vite 构建配置
├── eslint.config.js            # ESLint 配置
├── src/
│   ├── main.js                 # 应用入口（挂载 Vue + Pinia + Router）
│   ├── App.vue                 # 根组件
│   ├── style.css               # 全局样式
│   ├── pages/                  # 视图级页面
│   │   ├── HomePage.vue        首页（城市输入 + 参数配置）
│   │   ├── SuggestPage.vue     ca_suggest 方案建议列表
│   │   └── PlanPage.vue        核心规划展示页
│   ├── components/             # 可复用组件
│   │   ├── AmapMap.vue         高德 2D 地图视图
│   │   └── SchedulePanel.vue   每日行程列表
│   ├── router/
│   │   └── index.js            Vue Router 路由（/ /suggest /plan）
│   ├── services/
│   │   └── api.js              Axios 封装（/api/poi-lookup /suggest /plan /chat）
│   └── stores/
│       └── plan.js             Pinia store（方案状态管理）
```

## 组件树

```
App.vue                         [✅]
├── NavigationBar.vue           # 顶部导航/页面切换 [⏸ P2]
├── HomePage.vue                # 首页：城市输入 + 酒店选择 + 参数配置 [✅]
│   ├── CityInput.vue           [⏸ P2]
│   ├── DateRangePicker.vue     [⏸ P2]
│   └── ModeSelector.vue        # fast/deep 模式切换 [⏸ P2]
├── SuggestPage.vue             # ca_suggest 方案建议列表 [✅]
│   └── SuggestionCard.vue      # 每条建议的简要成本/天数展示 [⏸ P2]
├── PlanPage.vue                # 核心规划展示页 [✅]
│   ├── AmapMap.vue             # 高德 2D 地图视图 [✅]
│   │   └── RoutePolyline.vue   # 每日路径折线 [⏸ P2]
│   ├── SchedulePanel.vue       # 每日行程列表（左/下侧） [✅]
│   │   └── DayCard.vue         # 某一天：景点列表 + 时间线 [⏸ P2]
│   └── AgentChat.vue           # LLM Agent 聊天面板（右/下侧） [⏸ P2]
│       └── ChatMessage.vue     # 单条消息（用户/Agent） [⏸ P2]
└── HistoryPage.vue             # 历史方案记录 [⏸ P2]
```

## 关键文件说明

| 文件 | 说明 |
|------|------|
| `main.js` | 入口，注册 Pinia + Vue Router |
| `router/index.js` | 三个路由：`/`(Home) → `/suggest`(Suggest) → `/plan`(Plan) |
| `services/api.js` | 4 个 API 函数：`postPoiLookup` / `postSuggest` / `postPlan` / `postChat` |
| `stores/plan.js` | Pinia store，管理规划状态 |
| `index.html` | SPA 入口 HTML |
| `vite.config.js` | Vite 配置 + API 代理 |
| `eslint.config.js` | ESLint 规则 |
