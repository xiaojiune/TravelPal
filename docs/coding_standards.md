# 编码规范

## cdsd++: 

### 🚧 接口清单

🚧 清单粒度需明确边界：仅列模块顶层函数 + 类核心入口方法，不列 getter/辅助方法
🚧 明确 `__all__` 为公开 API 唯一真值，顶部注释清单仅用于快速预览（双源主从关系）
🛑 废弃补充版本号标注：当前项目无版本体系，暂不采纳

### 🚧 注释规范

🚧 已类型注解的函数，docstring 中 Args 省略参数类型，仅描述语义
🚧 统一 TODO/FIXME 格式（如 `# TODO: xxx` / `# FIXME: xxx`）
🚧 内部方法注释尺度：参数 ≤ 2 个且返回值简单时用单行 docstring；参数复杂时补充 Args/Returns
🛑 强制补充 Raises/Examples 块：择需补充，不做强制要求
🚧 测试代码（P2）注释标准：
    - 测试方法无需 docstring（方法名自文档化）
    - 类级可加一行简要说明测试范围
    - 仅以下场景加行内 Why 注释：
        - 回归测试（标注 issue/修复原因）
        - 参数化测试的数据集选择理由
        - 验证架构假设的关键测试（如 VNS 应优于 CA）

### 🚧 编码约定

🚧 新增 NumPy/Numba 专项约定：dtype 显式声明、njit 纯数值原则、矩阵维度语义全局统一
🚧 新增数据单位全局约定（距离 km、时间 小时）
🚧 禁止可变默认参数（list/dict 默认值用 None + 内部分支初始化）
🛑 配范本文件：vns.py 本身就是范本，不必另维护

### ⏸ 远期

⏸ 接入 ruff 等 lint 工具做自动化检查（后续专项处理）

---

## 接口清单规范

### 文件头路径注释

每个 `.py` 文件顶部标注模块路径：

```text
# src/engine/vns.py
```

### 接口清单（文件顶部）

对外暴露的接口在文件头部集中列出，每行格式为 `函数名(参数...) -> 返回值说明`：

```text
# ================== 接口清单 ==================
# VNSSolver(city_indices, spots_dict, ...) -> 求解器实例
# solver.solve(dis_matrix) -> dict
# build_real_data(poi_names, city, ...) -> (cost_matrix_hours, dist_matrix_km, ...)
```

### 接口变更工作流

修改函数签名或新增公开 API 时，遵循以下顺序：

1. 先更新 `__init__.py` 顶部的接口清单注释块
2. 再修改对应的实现文件
3. 确保接口清单与 `__all__` 列表保持同步
4. **接口删除或重命名**：遵循相同的先更新清单、再修改代码的顺序。对于重命名，建议保留旧名作为别名（`old_name = new_name`）并标记 `# Deprecated`，给予下游调用方过渡期。

### `__init__.py` 导出

使用 `__all__` 明确声明模块的公开 API，替代手写接口清单的维护负担：

```text
__all__ = ["VNSSolver", "CASolver", "cluster_and_solve"]
```

> 当前接口清单以手动注释块维护。未来如引入 Sphinx 等文档工具，可考虑从函数/类 Docstring 中自动提取接口文档，配合 `sphinx-apidoc` 生成，减少人工维护成本。

---

## 注释规范

### 注释优先级分层

按函数重要性分三级，不同层级投入不同注释深度：

| 层级 | 范围 | 注释要求 |
|------|------|---------|
| **P0** | 核心算法模块（vns.py、ca.py、clustering.py、fitness.py） | 三类注释完整覆盖：参数字典设计说明 + Google docstring + 行内 Why 注释 |
| **P1** | 编排/管道/工具（search.py、pipeline.py、amap_loader.py、cesium_utils.py） | Google docstring + 关键逻辑 Why 注释（跳过参数字典设计说明） |
| **P2** | 测试/config（tests/*.py、config.py） | 行内 Why 注释即可 |

### 段落分隔线

使用分隔线划分逻辑段落：

- `# ================== 段标题 ==================`  —— 主要段落
- `# ---------- 子段标题 ----------`               —— 子段落
- `# ***** 标注文字 *****`                         —— 需要强调的关键注释

```text
# ================== VNS 默认参数 ==================
# ---------- 适应度（带缓存） ----------
```

### 函数/方法注释

对外关键函数使用 Google 风格 docstring，Returns 需包含成本结构和取值范围：

```text
def analyze_solution(solution, dis_matrix, spots_dict, travel_speed, ...):
    """
    解析路径的详细成本与违规信息。

    Args:
        solution (List[int]): 路径序列。
        dis_matrix (np.ndarray): 距离矩阵。
        spots_dict (dict): 景点字典，每项含 {"tw": (start, end), "stay": float}。
        travel_speed (float): 行驶速度。

    Returns:
        Tuple[float, float, float, float, int]:
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

### 行内注释

关键逻辑用行内注释**传达设计意图（Why）而非仅描述行为（What）**：

```text
# 连续无改善计数递增，用于触发早停（避免无效迭代）
no_improve += 1

# 自适应机制：让历史上更有效的算子获得更高被选中概率，加速收敛
self.operator_weights[self.last_operator] *= 1.02

# 早期阶段，针对违规节点扰动可加速可行解的发现；后期则依赖自适应算子探索更广空间
sol = self._perturb_around(sol, target, op)

# VND 按 swap → inversion → insert → 2opt 顺序执行（经验排序，前期收敛最快）
self._local_search(sol, dis_matrix, 'swap')

# 主循环结束后对精英解额外执行 VND，提升最终解的质量稳定性
for _ in range(self.params['final_vnd_rounds']):
    refined = self._vnd(best_sol, dis_matrix)
```

对比案例：从 What 到 Why：

| 模式 | 差（What） | 好（Why） |
|------|-----------|----------|
| 无改善计数 | `no_improve += 1` | `# 连续无改善计数递增，用于触发早停（避免无效迭代）` |
| 算子选择 | `self._local_search(sol, 'swap')` | `# VND 按 swap → inversion → insert → 2opt 顺序执行（经验排序，前期收敛最快）` |
| 参数含义 | `PENALTY_START = 0.01` | `# 初始惩罚权重很小 → 允许探索不可行区域；后期逐渐增大到 1.0 → 强制收敛到可行解` |

### 参数配置注释

对复杂的配置项在定义处附带设计说明（常用于算法参数）：

```text
# 说明：压缩退火通过动态调整接受准则中惩罚项的权重来实现
# 初期 penalty_start 很小 → 对惩罚增加不敏感，允许探索不可行区域
# 后期逐渐增大到 1.0 → 与原始成本一致，强制收敛到可行解
```

### 参数设计说明

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

### 不需要注释的情况

- 逻辑清晰、不言自明的代码（如 `x = y + 1`）。
- 标准的、广泛使用的设计模式（如工厂模式、单例模式）。
- 类中的 getter 方法（如 `get_elite_pool()`）。

### 前端文件注释规范

Vue SFC / TypeScript 与 Python 注释的差异对照：

| 场景 | Python | Vue / TypeScript |
|------|--------|-----------------|
| 组件/函数注释 | Google docstring | JSDoc（`/** @param ... @returns ... */`） |
| 关键逻辑注释 | `#` Why 注释 | `//` Why 注释 |
| 接口/Props 说明 | 类型注解 + docstring | `defineProps` + JSDoc |
| 常量/配置 | 大写下划线 + 行内注释 | `const` + JSDoc |

注释深度参照 P0/P1 分层标准：
- **P0 等价**（核心组件如 CesiumMap.vue、AgentChat.vue）：JSDoc + 行内 Why 注释
- **P1 等价**（管道组件如 SchedulePanel.vue）：JSDoc
- **P2 等价**（基础组件如 DayCard.vue）：行内 Why 注释即可

---

## 编码约定

- **类型注解**：函数参数和返回值必须标注类型，Python 3.10+ 优先使用 `|` 语法而非 `Optional`/`Union`：

  ```text
  def parse_time(s: str | None) -> tuple[int, int] | None: ...
  ```

- **命名风格**：变量/函数使用 `snake_case`，类使用 `PascalCase`，常量使用 `UPPER_CASE`。

- **行宽**：不超过 100 字符。

- **导入顺序**：标准库 → 第三方库 → 项目内部模块，各组之间空一行。

- **路径处理**：使用 `pathlib.Path` 替代 `os.path`：

  ```text
  from pathlib import Path
  data_dir = Path("data") / "subdir"
  ```

- **魔术数字**：避免硬编码数值，用常量或枚举命名：

  ```text
  EARLY_WAIT_WEIGHT = 0.1
  MAX_RETRIES = 3
  ```

- **打印输出**：生产代码使用 `logging`，调试代码使用 `print` 但不应提交：

  ```text
  import logging
  logger = logging.getLogger(__name__)
  ```

- **独立运行入口**：每个模块可以保留 `if __name__ == "__main__":` 作为测试入口。

- **`__init__.py` 导出**：使用 `__all__` 明确声明模块的公开 API：

  ```text
  __all__ = ["VNSSolver", "CASolver", "cluster_and_solve"]
  ```
