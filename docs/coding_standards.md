# 编码规范

> 本规范参考原项目 `utils/` 目录下的代码风格制定。

## 注释要求

### 文件级别

每个 `.py` 文件顶部标注模块路径（旧项目惯例，便于 IDE 导航）：

```text
# utils/vns_plus.py
```

对外暴露的接口在文件头部集中列出，格式为 `函数签名 -> 返回值说明`：

```text
# ================== 接口清单 ==================
# VNSPlusSolver(city_indices, spots_dict, ...) -> 求解器实例
# solver.solve(dis_matrix) -> {'best_solution', 'best_cost', ...}
# build_real_data(poi_names, city, ...) -> (cost_matrix_hours, dist_matrix_km, ...)
```

> 接口清单需要手动维护，建议在 `__init__.py` 中用 `__all__` 替代，避免签名变更后清单过期腐烂：
> ```text
> __all__ = ["VNSPlusSolver", "build_real_data"]
> ```

### 段落级别

使用分隔线划分逻辑段落：

- `# ================== 段标题 ==================`  —— 主要段落
- `# ---------- 子段标题 ----------`               —— 子段落
- `# ***** 标注文字 *****`                         —— 需要强调的关键注释

示例：

```text
# ================== VNS+ 默认参数 ==================
# ================== 高德 API 配置 ==================
# ---------- 适应度（带缓存） ----------
# ---------- 初始解（默认最近邻） ----------
# ***** 压缩退火参数（正确版本） *****
```

### 函数/方法级别

对外的关键函数使用 Google 风格的 docstring：

```text
def build_real_data(poi_names, coords, delay=0.4):
    """
    根据景点名称和坐标列表构建真实数据。

    Args:
        poi_names (List[str]): 景点名称列表。
        coords (List[Tuple[float, float]]): 预先获取好的坐标列表。
        delay (float): API 调用间隔秒数。

    Returns:
        Tuple[np.ndarray, np.ndarray, dict]: cost_matrix_hours, dist_matrix_km, polylines_dict
    """
```

内部方法使用单行 docstring：

```text
def _perturb_around(self, route, target, op):
    """针对特定节点进行扰动（对其附近片段操作）"""
```

### 行内注释

关键逻辑用行内注释说明设计意图：

```text
# Numba预提取数组
self.spots_start = np.array([...])

# 适应度缓存（直接启用，无开关）
self.fitness_cache = {}

# 压缩系数（随迭代进度线性增长）
compress_factor = start_compress + (end_compress - start_compress) * progress
```

### 参数配置注释

对复杂的配置项在定义处附带说明（常用于算法参数）：

```text
# 说明：压缩退火通过动态调整接受准则中惩罚项的权重来实现
# 初期 penalty_start 很小 → 对惩罚增加不敏感，允许探索不可行区域
# 后期逐渐增大到 1.0 → 与原始成本一致，强制收敛到可行解
```

## 不需要注释的情况

- 逻辑清晰、不言自明的代码（如 `x = y + 1`）。
- 标准的、广泛使用的设计模式（如工厂模式、单例模式）。
- 类中的 getter 方法（如 `get_elite_pool()`）。

## 编码约定

- **类型注解**：函数参数和返回值必须标注类型，Python 3.10+ 优先使用 `|` 语法而非 `Optional`/`Union`：

  ```text
  # ✅ 推荐
  def parse_time(s: str | None) -> tuple[int, int] | None: ...

  # ❌ 旧写法
  def parse_time(s: Optional[str]) -> Optional[Tuple[int, int]]: ...
  ```

- **命名风格**：变量/函数使用 `snake_case`，类使用 `PascalCase`，常量使用 `UPPER_CASE`。

- **行宽**：不超过 100 字符。

- **导入顺序**：标准库 → 第三方库 → 项目内部模块，各组之间空一行。

- **路径处理**：使用 `pathlib.Path` 替代 `os.path`：

  ```text
  # ✅ 推荐
  from pathlib import Path
  data_dir = Path("data") / "subdir"

  # ❌ 旧写法
  import os
  data_dir = os.path.join("data", "subdir")
  ```

- **魔术数字**：避免硬编码数值，用常量或枚举命名：

  ```text
  # ✅ 推荐
  EARLY_WAIT_WEIGHT = 0.1
  MAX_RETRIES = 3

  # ❌ 不推荐
  time_penalty += wait * 0.1
  ```

- **打印输出**：生产代码使用 `logging`，调试代码使用 `print` 但不应提交：

  ```text
  import logging
  logger = logging.getLogger(__name__)
  logger.warning("POI 请求失败: %s", poi_name)
  ```

- **独立运行入口**：每个模块可以保留 `if __name__ == "__main__":` 作为测试入口：

  ```text
  if __name__ == "__main__":
      # 快速测试当前模块逻辑
      result = solve_tsp(...)
      print(result)
  ```

- **`__init__.py` 导出**：使用 `__all__` 明确声明模块的公开 API：

  ```text
  __all__ = ["VNSPlusSolver", "SASolver", "build_real_data"]
  ```
