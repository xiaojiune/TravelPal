# 编码规范

## 接口清单规范

### 文件头路径注释

每个 `.py` 文件顶部标注模块路径：

```text
# src/engine/vns.py
```

### 接口清单（文件顶部）

对外暴露的接口在文件头部集中列出，格式为 `函数签名 -> 返回值说明`：

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

### `__init__.py` 导出

使用 `__all__` 明确声明模块的公开 API，替代手写接口清单的维护负担：

```text
__all__ = ["VNSSolver", "CASolver", "cluster_and_solve"]
```

> 当前接口清单以手动注释块维护。未来如引入 Sphinx 等文档工具，可考虑从函数/类 Docstring 中自动提取接口文档，配合 `sphinx-apidoc` 生成，减少人工维护成本。

---

## 注释规范

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

对外关键函数使用 Google 风格 docstring：

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

### 参数配置注释

对复杂的配置项在定义处附带设计说明（常用于算法参数）：

```text
# 说明：压缩退火通过动态调整接受准则中惩罚项的权重来实现
# 初期 penalty_start 很小 → 对惩罚增加不敏感，允许探索不可行区域
# 后期逐渐增大到 1.0 → 与原始成本一致，强制收敛到可行解
```

### 不需要注释的情况

- 逻辑清晰、不言自明的代码（如 `x = y + 1`）。
- 标准的、广泛使用的设计模式（如工厂模式、单例模式）。
- 类中的 getter 方法（如 `get_elite_pool()`）。

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
