# 编码规范

## 后端

### 注释四级体系

| 等级 | 特征 | 目标 |
|------|------|------|
| P0 不合格 | 无注释 / 函数名复述 / 参数缺失 | 不允许 |
| P1 合格 | 一句话功能 + 完整 Args/Returns | 底线要求 |
| P2 优秀 | 设计意图 + 边界约定 + 异常行为 | 追求目标 |
| P3 详尽 | 逐行解释算法与数学推导 | 仅核心算法模块 |

当前注释水平处于 P1 合格线。优化目标：P1→P2，**不是 P0→P1**。

### 接口变更工具流

修改函数签名或新增公开 API 时，遵循以下顺序：

1. **先更新 `__init__.py` 的 `__all__` 列表**
2. **再修改**对应的实现文件
3. **确保**`__all__` 中已包含新增的公开 API
4. **重命名或删除**：遵循相同的先更新清单、再修改代码的顺序。对于重命名，建议保留旧名作为别名（`old_name = new_name`）并标记 `# Deprecated`，给予下游调用方过渡期

### 编码约定

#### 通用约定

**类型注解**：函数参数和返回值必须标注类型，Python 3.10+ 优先使用 `|` 语法而非 `Optional`/`Union`：

```text
def parse_time(s: str | None) -> tuple[int, int] | None: ...
```

**类型注解执行边界**：
- 强制范围：公开 API（`__all__` 导出的函数/类）必须完整标注类型
- 推荐范围：内部私有函数推荐标注，简单单行函数可豁免
- NumPy 补充：数组统一标注为 `np.ndarray`，关键矩阵在 docstring 补充维度说明

**命名风格**：变量/函数使用 `snake_case`，类使用 `PascalCase`，常量使用 `UPPER_CASE`。

**行宽**：不超过 100 字符。

**导入顺序**：标准库 → 第三方库 → 项目内部模块，各组之间空一行。函数内 import 需注释说明原因：

```text
# 函数内导入，避免循环依赖
from backend.engine.pipeline import _rebuild_schedule
```

**路径处理**：使用 `pathlib.Path` 替代 `os.path`：

```text
from pathlib import Path
data_dir = Path("data") / "subdir"
```

**魔术数字**：避免硬编码数值，用常量或枚举命名：

```text
EARLY_WAIT_WEIGHT = 0.1
MAX_RETRIES = 3
```

**打印输出**：生产代码使用 `logging`，调试代码使用 `print` 但不应提交：

```text
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

```text
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
| `travel_speed` | 无量纲 | 占位参数，真实数据未使用，固定 1.0 |
| `stay` | 分钟 | 景点停留时间 |
| `tw` | 分钟 | 时间窗 (start, end)，0-1440 |

### 接口清单规范

使用 `__all__` 明确声明模块的公开 API，替代手写接口清单的维护负担：

```text
__all__ = ["VNSSolver", "CASolver", "cluster_and_solve"]
```

**净化规则**：
- `__all__` 不得包含下划线开头的私有函数，如 `data/__init__.py` 的 `_parse_opentime_to_tw` 应移除

> 当前接口清单以手动注释块维护。未来如引入 Sphinx 等文档工具，可考虑从函数/类 Docstring 中自动提取接口文档，配合 `sphinx-apidoc` 生成，减少人工维护成本。

### 注释规范

#### 注释优先级分层

按函数重要性分三级，不同层级投入不同注释深度：

| 层级 | 范围 | 注释要求 |
|------|------|---------|
| **L0** | 核心算法（vns.py、ca.py、clustering.py、fitness.py） | P2~P3 标准：参数设计说明 + Google docstring + 行内 Why |
| **L1** | 编排/管道/工具（search.py、pipeline.py、amap_loader.py） | P1~P2 标准：Google docstring + 关键逻辑 Why |
| **L2** | 测试/config（tests/*.py、config.py） | P0~P1 标准：行内 Why 即可 |

#### 段落分隔线

- `# ================== 段标题 ==================` —— 主要段落
- `# ---------- 子段标题 ----------` —— 子段落
- `# ***** 标注文字 *****` —— 需要强调的关键注释

```text
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

```text
def _perturb_around(self, route, target, op):
    """针对特定节点进行扰动（对其附近片段操作）

    Args:
        op (str): 使用的扰动算子，可选 'swap'/'inversion'/'insert'。
    """
```

Raises 段在涉及外部输入时必写：

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

```text
"""从方案中移除指定景点并重新求解。

设计说明：优先保留原有行程分组结构，仅对受影响的分组做局部重算；
相比全量重新规划速度更快，且对原有行程改动最小，用户体验更连贯。
索引 0（酒店起点）不可删除。入参不会被修改。
"""
```

数据结构约定在行内注释中一并标注：

```text
spots_dict: dict[int, dict]
    # 格式: {index: {"name": str, "tw": (start, end), "stay": int, "x": float, "y": float}}
    # 索引 0 固定为酒店起点，不可删除
```

#### 参数配置注释

对复杂的配置项在定义处附带设计说明（常用于算法参数）：

```text
# 说明：压缩退火通过动态调整接受准则中惩罚项的权重来实现
# 初期 penalty_start 很小 → 对惩罚增加不敏感，允许探索不可行区域
# 后期逐渐增大到 1.0 → 与原始成本一致，强制收敛到可行解
```

#### 参数设计说明

在默认参数字典上方用多行注释说明每个参数。格式：**意图 → 建议默认值/范围 → 调参方向**：

```text
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

### 注释四级体系

```text
// TODO: 前端部分待填充——四级体系定义（P0-P3）同后端，示例使用 JSDoc 格式
```

### 接口变更工具流

```text
// TODO: 前端部分待填充——组件 Props 变更 / 事件 emit 变更 / Router 变更流程
```

### 编码约定

```text
// TODO: 前端部分待填充——Vue 3 Composition API / TypeScript / 命名风格 / 组件文件组织
```

### 接口清单规范

```text
// TODO: 前端部分待填充——组件 Props 清单 / Emits 清单 / 页面路由清单
```

### 注释规范

```text
// TODO: 前端部分待填充——JSDoc 格式 / Props 注释 / 页面段注释（pages/ 目录）
// 注释深度参照后端 P0/P1/P2 分层标准：
// - P0 等价钱（核心组件 AmapMap.vue、AgentChat.vue）：JSDoc + 行内 Why
// - P1 等价钱（管道组件 SchedulePanel.vue）：JSDoc
// - P2 等价钱（基础组件 DayCard.vue）：行内 Why
// - 页面级文件使用段注释：
//   // ====== 状态定义 ======
//   // ====== 计算属性 ======
//   // ====== 数据操作 ======
//   // ====== 生命周期 ======
```
