# 编码规范

## 注释四级体系

项目前后端统一使用 P0-P3 四级注释体系：

| 等级 | 特征 | 目标 |
|------|------|------|
| P0 不合格 | 无注释 / 函数名复述 / 参数缺失 | 不允许 |
| P1 合格 | 一句话功能 + 完整 Args/Returns | 底线要求 |
| P2 优秀 | 设计意图 + 边界约定 + 异常行为 | 追求目标 |
| P3 详尽 | 逐行解释算法与数学推导 | 仅核心算法模块 |

前后端的 Lx 分级及具体注释要求见各自域内。

## 后端

当前注释水平：后端核心模块（vns/ca/clustering）达 P2，编排模块（pipeline/search）达 P1~P2，测试达 P0~P1。

### 接口变更工具流

修改函数签名或新增公开 API 时，遵循以下顺序：

1. **先更新 `__init__.py` 的 `__all__` 列表**
2. **再修改**对应的实现文件
3. **确保**`__all__` 中已包含新增的公开 API
4. **重命名或删除**：遵循相同的先更新清单、再修改代码的顺序。对于重命名，建议保留旧名作为别名（`old_name = new_name`）并标记 `# Deprecated`，给予下游调用方过渡期

### 编码约定

#### 通用约定

**类型注解**：函数参数和返回值必须标注类型，Python 3.10+ 优先使用 `|` 语法而非 `Optional`/`Union`：

```python
def parse_time(s: str | None) -> tuple[int, int] | None: ...
```

**类型注解执行边界**：
- 强制范围：公开 API（`__all__` 导出的函数/类）必须完整标注类型
- 推荐范围：内部私有函数推荐标注，简单单行函数可豁免
- NumPy 补充：数组统一标注为 `np.ndarray`，关键矩阵在 docstring 补充维度说明

**命名风格**：变量/函数使用 `snake_case`，类使用 `PascalCase`，常量使用 `UPPER_CASE`。

**行宽**：不超过 100 字符。

**导入顺序**：标准库 → 第三方库 → 项目内部模块，各组之间空一行。函数内 import 需注释说明原因：

```python
# 函数内导入，避免循环依赖
from backend.engine.pipeline import _rebuild_schedule
```

**路径处理**：使用 `pathlib.Path` 替代 `os.path`：

```python
from pathlib import Path
data_dir = Path("data") / "subdir"
```

**魔术数字**：避免硬编码数值，用常量或枚举命名：

```python
EARLY_WAIT_WEIGHT = 0.1
MAX_RETRIES = 3
```

**打印输出**：生产代码使用 `logging`，调试代码使用 `print` 但不应提交：

```python
import logging
logger = logging.getLogger(__name__)
```

**日志级别约定**：
- DEBUG：开发调试用，不提交生产
- INFO：正常业务流程节点
- WARNING：异常但可自动恢复
- ERROR：流程中断致命错误
- 异常优先使用 Python 内置类型（ValueError/TypeError/KeyError），不滥用自定义异常

**TODO/FIXME 格式**：统一使用 `# TODO: xxx` / `# FIXME: xxx` 格式，禁止其他变体。

**独立运行入口**：每个模块可以保留 `if __name__ == "__main__":` 作为测试入口。

**禁止可变默认参数**：`list`/`dict` 默认值用 `None` + 内部分支初始化：

```python
def solve(dis_matrix, initial_solution: list[int] | None = None):
    if initial_solution is None:
        initial_solution = []
```

**单函数长度软约束**：单函数代码建议不超过 80 行，核心算法可放宽至 120 行。超过后优先拆分子函数。

#### NumPy / Numba 专项

- `dtype` 显式声明（`np.float64` 而非浮点字面量）
- `njit` 只用于纯数值计算，不传入 Python 对象
- 矩阵维度语义全局统一：行 = 出发节点，列 = 到达节点

#### 数据单位全局约定

| 变量名 | 单位 | 说明 |
|--------|------|------|
| `dist_matrix` | km | 距离矩阵 |
| `cost_matrix` | 分钟 | 耗时矩阵（cost_matrix_hours * 60 后的值） |
| `travel_speed` | 无量纲 | 占位参数，use_real_time_matrix=False 时固定 1.0 |
| `use_real_time_matrix` | — | bool 标志：False 用标准距离矩阵，True 用高德真实时间矩阵 |
| `stay` | 分钟 | 景点停留时间 |
| `tw` | 分钟 | 时间窗 (start, end)，0-1440 |

### 接口清单规范

使用 `__all__` 明确声明模块的公开 API，替代手写接口清单的维护负担：

```text
__all__ = ["VNSSolver", "CASolver", "cluster_and_solve"]
```

**__all__ 生成规范**：
- `__all__` 不得包含下划线开头的私有函数
- 新增公开 API 时，先更新 `__init__.py` 的 `__all__` 列表，再运行 `tools/sync_all.py` 同步导出

### 注释规范

#### 注释优先级分层

按函数重要性分三级，不同层级投入不同注释深度：

| 层级 | 范围 | 注释要求 | 数据方案 |
|------|------|---------|---------|
| **L0** | 核心算法（vns.py、ca.py、clustering.py、fitness.py） | P2~P3 标准：参数设计说明 + Google docstring + 行内 Why | TypedDict |
| **L1** | 编排/管道/工具（search.py、pipeline.py、amap_loader.py） | P1~P2 标准：Google docstring + 关键逻辑 Why | TypedDict |
| **L2** | 测试/config（tests/*.py、config.py） | P0~P1 标准：行内 Why 即可 | dict 无需约束 |

### 数据模型选型

按运行时需求分层，API 边界用 Pydantic，内部传递用 TypedDict：

| 场景 | 推荐方案 | 运行时校验 | 说明 |
|------|---------|:---------:|------|
| API 请求/响应（schemas.py） | Pydantic BaseModel | ✅ | FastAPI 原生支持，自动生成 OpenAPI 文档 |
| 内部数据结构（spots_dict、poi_cache） | TypedDict | ❌ | 轻量，零运行时开销，只做类型约束 |
| 跨模块业务对象（SpotDict / PlanResult） | TypedDict | ❌ | 内部传递轻量，零运行时开销 |
| 配置/环境变量 | Pydantic BaseSettings | ✅ | 可自动加载 .env |
| 函数参数/返回值 | TypedDict 或 Pydantic | 按需 | 取决于是否需要运行时校验 |

**命名约定**：内部用 `XxxDict`（如 `SpotDict`、`PoiCache`），API 用 `XxxModel`（如 `PlanRequest` 等已有 Pydantic 类不动）。

**升级路径**：TypedDict → Pydantic Model 是平滑的，只需替换类型声明。初始化建议先用 TypedDict，有校验需求时再升级。

#### 段落分隔线

- `# ================== 段标题 ==================` —— 主要段落
- `# ---------- 子段标题 ----------` —— 子段落
- `# ***** 标注文字 *****` —— 需要强调的关键注释

```python
# ================== VNS 默认参数 ==================
# ---------- 适应度（带缓存） ----------
```

#### 函数/方法注释

对外关键函数使用 Google 风格 docstring。已类型注解的参数，docstring Args 中省略参数类型，仅描述语义。Returns 需包含成本结构和取值范围：

```text
def analyze_solution(solution, dis_matrix, spots_dict, travel_speed, ...):
    """解析路径的详细成本与违规信息。

    Args:
        solution: 路径序列。
        dis_matrix: 距离矩阵。
        spots_dict: 景点字典，每项含 {"tw": (start, end), "stay": float}。
        travel_speed: 行驶速度。

    Returns:
        tuple[float, float, float, float, int]:
            cost (总成本 = 距离 + 等待 + 迟到 + 惩罚),
            dist (总行驶距离),
            wait_pen (总等待时间),
            late_pen (总迟到时间),
            violations (违规节点数，0 表示完全可行)
    """
```

内部方法使用单行 docstring：

```python
def _perturb_around(self, route, target, op):
    """针对特定节点进行扰动（对其附近片段操作）

    Args:
        op (str): 使用的扰动算子，可选 'swap'/'inversion'/'insert'。
    """
```

### Raises 段要求

涉及外部输入时必须在 docstring 中标注可能抛出的异常：

```text
Raises:
    ValueError: 未找到对应名称的景点时抛出。
```

#### 行内注释

关键逻辑用行内注释**传达设计意图（Why）而非仅描述行为（What）**：

```text
# 连续无改善计数递增，用于触发早停（避免无效迭代）
no_improve += 1

# 自适应机制：让历史上更有效的算子获得更高被选中概率，加速收敛
self.operator_weights[self.last_operator] *= 1.02

# VND 按 swap → inversion → insert → 2opt 顺序执行（经验排序，前期收敛最快）
self._local_search(sol, dis_matrix, 'swap')

# 删除景点后索引不连续，重新映射为 0,1,2... 对齐矩阵维度
mapping = {old: new for new, old in enumerate(sorted(remaining))}
new_spots = {mapping[i]: spots_dict[i] for i in remaining}
```

对比案例：

| 模式 | 差（What） | 好（Why） |
|------|-----------|----------|
| 无改善计数 | `no_improve += 1` | `# 连续无改善计数递增，用于触发早停（避免无效迭代）` |
| 算子选择 | `self._local_search(sol, 'swap')` | `# VND 按 swap → inversion → insert → 2opt 顺序执行（经验排序，前期收敛最快）` |
| 参数含义 | `PENALTY_START = 0.01` | `# 初始惩罚权重很小 → 允许探索不可行区域；后期逐渐增大到 1.0 → 强制收敛到可行解` |

P2 阶段需补充的前置设计意图说明，在函数 docstring 中而非行内注释表达：

```python
"""从方案中移除指定景点并重新求解。

设计说明：优先保留原有行程分组结构，仅对受影响的分组做局部重算；
相比全量重新规划速度更快，且对原有行程改动最小，用户体验更连贯。
索引 0（酒店起点）不可删除。入参不会被修改。
"""
```

数据结构约定在行内注释中一并标注：

```python
spots_dict: dict[int, dict]
    # 格式: {index: {"name": str, "tw": (start, end), "stay": int, "x": float, "y": float}}
    # 索引 0 固定为酒店起点，不可删除
```

> **注意**：修改代码后检查函数/类上方的文档注释和行内注释是否与逻辑同步，保持参数列表、返回值、设计理由的描述与实际代码一致。

#### 参数配置注释

对复杂的配置项在定义处附带设计说明（常用于算法参数）：

```python
# 说明：压缩退火通过动态调整接受准则中惩罚项的权重来实现
# 初期 penalty_start 很小 → 对惩罚增加不敏感，允许探索不可行区域
# 后期逐渐增大到 1.0 → 与原始成本一致，强制收敛到可行解
```

#### 参数设计说明

在默认参数字典上方用多行注释说明每个参数。格式：**意图 → 建议默认值/范围 → 调参方向**：

```python
# VNS_DEFAULT_PARAMS 设计说明：
# - max_iter：主循环迭代次数，决定搜索深度。建议 100-300。增大→更充分搜索，增大耗时。
# - shaking_neighbors：抖动强度候选集合大小。越大扰动越剧烈，利于跳出局部最优。
# - no_improve_limit：连续无改善阈值，控制早停敏感度。越小→越早收敛。
# - sa_initial_temp / sa_cooling_rate：控制 SA 接收准则的退火速度。
# - elite_size：精英池容量，保留历史上最优解结构。
# - final_vnd_rounds：主循环结束后对精英解额外进行 VND 的轮数，提升最终解稳定性。
VNS_DEFAULT_PARAMS = { ... }
```

#### 不需要注释的情况

- 逻辑清晰、不言自明的代码（如 `x = y + 1`）
- 标准的、广泛使用的设计模式（如工厂模式、单例模式）
- 类中的 getter 方法（如 `get_elite_pool()`）

#### 测试代码注释（P2）

- 测试方法无需 docstring（方法名自文档化）
- 类级可加一行简要说明测试范围
- 仅以下场景加行内 Why 注释：
  - 回归测试（标注 issue/修复原因）
  - 参数化测试的数据集选择理由
  - 验证架构假设的关键测试（如 VNS 应优于 CA）

## 前端

### 接口变更工具流

修改组件 API 或新增路由时，遵循以下顺序：

**Props/Emits 变更**：
1. **先更新组件 Props 定义**（`defineProps` 的 type + default）
2. **再更新**父组件的传参调用
3. **若组件被多个父组件使用**，全局搜索引用逐一适配

**路由变更**：
1. **先在 `router/index.ts` 注册路由**（含 `path` + `name` + 懒加载）
2. **再实现**对应的页面组件
3. **最后更新**导航链接（`router.push` / `<router-link>`）

**Store 变更**：
1. **先在 store 中新增状态/方法**（setup store 的 `return` 中暴露）
2. **再更新**使用该 store 的组件

### 编码约定

**语法**：使用 `<script setup>` + Composition API。状态用 `ref()` 而非 `reactive()`，派生值用 `computed()`。

**命名风格**：
- 组件文件：`PascalCase.vue`（如 `SchedulePanel.vue`）
- 页面文件：`PascalCase.vue`（如 `HomePage.vue`）
- 服务/工具文件：`camelCase.ts`（如 `api.ts`、`types.ts`）
- 目录：全小写（`stores/`、`services/`、`components/`、`pages/`）
- 导出函数/变量：`camelCase`
- Pinia store：`use` 前缀 + `Store` 后缀（`usePlanStore`）

**导入顺序**：Vue/Pinia → 第三方库 → 项目内部模块，各组之间空一行。

```ts
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'

import { usePlanStore } from '@/stores/plan'
import { postSuggest } from '@/services/api'

import AmapMap from '@/components/AmapMap.vue'
```

**Composition API 结构约定**（`<script setup>` 内按序排列）：

```ts
// 1. 外部导入（import）

// 2. Store / Router
const planStore = usePlanStore()
const router = useRouter()

// 3. Props / Emits
const props = defineProps<{ routes: any[]; amapKey: string }>()

// 4. 响应式状态
const loading = ref(false)
const error = ref('')

// 5. 计算属性
const hasResult = computed(() => planStore.result !== null)

// 6. 生命周期
onMounted(() => { /* init */ })
onBeforeUnmount(() => { /* cleanup */ })

// 7. 事件处理 / 方法
function handleSubmit() { /* ... */ }
function onRemove(index: number) { /* ... */ }

// 8. 侦听器（watch 放在最后）
watch(() => props.routes, (val) => { /* ... */ }, { deep: true })
```

**Props 定义**：使用 TypeScript 泛型定义 Props 接口，同时声明 `type` 和 `default`。

```ts
interface Props {
  dailySchedules?: ScheduleItem[][]
  highlightDay?: number
  onRemovePoi?: (dayIndex: number, spotId: number) => void
}
const props = withDefaults(defineProps<Props>(), {
  dailySchedules: () => [],
  highlightDay: 0,
  onRemovePoi: undefined,
})
```

**父子通信**：使用回调函数 prop 而非 `defineEmits`（当前项目约定）。

**API 服务**：使用 axios 实例，`baseURL: '/api'`，在 service 层解包 `response.data`。

```ts
import axios from 'axios'
const http = axios.create({ baseURL: '/api' })

export function postPoiLookup(city: string, names: string[]) {
  return http.post('/poi-lookup', { city, names }).then(r => r.data)
}
```

**组件 Props 直接绑定**：使用 `v-bind` 逐个传递而非对象展开。

- 组件根节点：根元素为 class 挂钩时，模板中保持可读的 `template`，不混入逻辑

### 接口清单规范

**组件级清单**：在组件定义处使用注释块声明公开 API。

```ts
// SchedulePanel.vue 公开接口
// Props:
//   dailySchedules: 每日行程数组 [{day, spots, ...}]
//   onRemovePoi:    删除景点回调 (dayIndex, spotId) => void
```

**路由清单**：路由集中定义在 `router/index.ts`，所有页面懒加载。

```ts
const routes: RouteRecordRaw[] = [
  { path: '/', name: 'Home', component: () => import('@/pages/HomePage.vue') },
  { path: '/suggest', name: 'Suggest', component: () => import('@/pages/SuggestPage.vue') },
  { path: '/plan', name: 'Plan', component: () => import('@/pages/PlanPage.vue') },
]
```

**Store 清单**：Pinia store 通过 `return` 显式暴露的接口即为公开 API。

```ts
return { city, spots, planResult, buildRequest, reset }
```

### 注释规范

#### 注释优先级分层

按文件重要性分三级：

| 层级 | 范围 | 注释要求 | 数据方案 |
|------|------|---------|---------|
| **L0** | 核心复杂组件（AmapMap.vue、ChatMessage.vue） | P2~P3 标准：JSDoc + 行内 Why + 设计意图 | TypedDict/Pydantic |
| **L1** | 管道/展示组件（SchedulePanel.vue、HomePage.vue） | P1~P2 标准：JSDoc + 关键逻辑 Why | TypedDict |
| **L2** | 页面容器 / store / 工具（SuggestPage.vue、stores/*.ts） | P1 标准：组件职责 + 行内 Why | Interface |

#### 按文件类型注释策略

##### `.vue` 文件

页面级（`pages/`）使用段注释区分逻辑区域：

```html
<script setup>
// ====== 状态定义 ======
const loading = ref(false)
const error = ref('')

// ====== 计算属性 ======
const totalDays = computed(() => planStore.planResult?.days ?? 0)

// ====== 数据操作 ======
function handleSearch() { ... }
function handleAdjust(day, spots) { ... }

// ====== 生命周期 ======
onMounted(() => { ... })
</script>
```

组件级（`components/`）使用 JSDoc + 行内 Why：

```html
<script setup>
/**
 * AmapMap — 高德 2D 地图视图
 *
 * 职责：接收规划结果中的每日路径数据，在地图上渲染折线和景点标记。
 * 设计说明：路由数组为空时显示空白地图（非加载态），
 * 便于父组件分步加载数据时保持地图实例不销毁。
 */
const props = defineProps({
  /** 每日路径数组 [{day, route, duration, ...}] */
  routes: { type: Array, default: () => [] },
  /** 景点字典 {index: {name, x, y, ...}} */
  spots: { type: Object, default: () => ({}) },
  /** 高亮某一天（-1 表示全部） */
  highlightDay: { type: Number, default: -1 },
  /** 高德 JS API Key */
  amapKey: { type: String, required: true },
})
</script>
```

##### `services/*.ts` 文件

函数级 JSDoc：

```ts
/**
 * 查询景点 POI 坐标。
 * @param city - 城市名
 * @param names - 景点名称列表
 */
export function postPoiLookup(city: string, names: string[]) {
  return http.post('/poi-lookup', { city, names }).then(r => r.data)
}
```

##### `stores/*.ts` 文件

Store 职责说明 + 关键方法 JSDoc：

```ts
/**
 * planStore — 规划流程状态管理
 *
 * 职责：承载从输入到结果的完整数据流，跨页面共享。
 * 生命周期：HomePage 写入 → SuggestPage/PlanPage 读取
 */
export const usePlanStore = defineStore('plan', () => {
  const city = ref('')
  const spots = ref<SpotFormItem[]>([])
  // ...

  /** 构造请求参数，nDays 为 null 时走 suggest 模式 */
  function buildRequest(nDays: number | null): PlanRequestPayload { /* ... */ }

  return { city, spots, planResult, buildRequest, reset }
})
```

##### `router/index.ts`

Router 配置无需 JSDoc，路由 path 和 name 自文档化。

行内注释原则与后端一致（传达 Why 而非 What），参见后端「行内注释」节。

#### 不需要注释的情况

- 模板中 `v-if`/`v-for` 等 Vue 内置指令
- 标准 Pinia 调用（`store.xxx` 赋值）
- 标准 Router 调用（`router.push`）

#### 模板注释

模板中仅当逻辑分支意图不明显时加注释：

```vue
<!-- 优先展示建议列表，无数据时显示空态提示 -->
<div v-if="suggestions.length" class="suggestion-list">
  <SuggestionCard v-for="s in suggestions" :key="s.id" ... />
</div>
<p v-else class="empty-hint">暂无建议，请调整输入后重试</p>
```

#### Props 默认值注释（P2）

复杂默认值或特殊约定在 Props 定义处附带说明：

```ts
interface Props {
  /** 高亮某一天（-1 表示全部显示，0/1/2... 指定某一天） */
  highlightDay?: number
  /** 不传则隐藏删除按钮（纯展示模式） */
  onRemovePoi?: (dayIndex: number, spotId: number) => void
}
const props = withDefaults(defineProps<Props>(), {
  highlightDay: -1,
  onRemovePoi: undefined,
})
```

### 组件粒度与逻辑复用

**SFC 拆分原则**：
- 模板超过 150 行 → 考虑拆分
- 有独立状态管理逻辑 → 考虑拆分
- 可被多个页面复用 → 必须拆分
- 与父组件强耦合且仅使用一次 → 可保持内联

**Composable 提取原则**：
- 相同业务逻辑出现 2 次以上 → 提取为 composable
- 命名以 `use` 开头，如 `usePlanning`、`usePoiSearch`

**Store 互引约定**：
- store 之间避免直接通过 `useXxxStore()` 互相引用（造成隐式循环依赖）
- 共享状态通过 composable 统一管理，或由调用方（页面）在组合时传入

**命名规范**：
- 组件文件：`PascalCase.vue`
- 服务/工具文件：`camelCase.ts`
- 目录名：`kebab-case`

### 反模式 / 不推荐

以下做法与项目约定冲突，应避免：

| 反模式 | 推荐做法 | 后果 |
|--------|----------|------|
| `reactive()` 包裹对象后在模板或计算中解构 | 优先用 `ref()`；如需深度响应才用 `reactive()`，直接使用不解构 | 解构后失去响应性追踪，变更不触发重渲染 |
| 组件 Props 用 `v-bind="obj"` 对象展开 | 逐一传递各 prop，调用处可读 | 数据来源不透明，难以定位未定义 prop 的传值 |
| 组件内 `async setup` | 异步初始化放在 `onMounted` 中处理 | setup 不支持 async，编译不报错但运行时行为未定义 |
| 模板中混入复杂表达式 | 计算逻辑放入 `computed`，模板只做渲染 | 模板难以测试和调试，表达式变更时容易遗漏 
