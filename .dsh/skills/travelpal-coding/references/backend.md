# 后端编码规范（TravelPal backend）

> 写/改常规后端代码（API、schemas、数据模型、服务）时的规范。VNS 引擎部分见 `engine.md`。

## Lx 注释分级（后端）

- 核心模块（vns/ca/clustering）：达 P2
- 编排模块（pipeline/search）：P1~P2
- 测试：P0~P1

## 接口变更工具流

修改函数签名或新增公开 API 时，按顺序：
1. 先更新 `__init__.py` 的 `__all__` 列表
2. 再改对应的实现文件
3. 确保 `__all__` 已包含新增的公开 API
4. 重命名/删除：先更新清单再改代码；重命名保留旧名作别名（`old_name = new_name`）标 `# Deprecated`

## 编码约定

- **类型注解**：参数/返回值必须标注。Python 3.10+ 用 `|` 语法（不用 `Optional`/`Union`）。
  - 强制：公开 API（`__all__` 导出）必须完整标注
  - 推荐：内部私有函数；简单单行函数可豁免
  - NumPy：数组标 `np.ndarray`，关键矩阵在 docstring 补维度
- **命名**：变量/函数 `snake_case`，类 `PascalCase`，常量 `UPPER_CASE`。
- **行宽**：≤120 字符。
- **依赖分组**：按「生产镜像或部署流程是否需要它」判定。
  - `main` 组：生产运行/部署需要（FastAPI/Celery/alembic/redis）
  - `dev` 组：纯开发工具（pytest/ruff/pyright）
  - 判定：部署或 `poetry export`（仅导出 main）是否执行它——是则 main，否则 dev。
- **导入顺序**：标准库 → 第三方 → 项目内部，组间空行；函数内 import 注释原因。
- **路径处理**：用 `pathlib.Path`，不用 `os.path`。
- **魔术数字**：用常量/枚举命名，不硬编码。
- **打印**：生产用 `logging`；调试 `print` 不提交。
- **日志级别**：DEBUG(调试)/INFO(正常)/WARNING(可恢复异常)/ERROR(致命)。异常用内置类型。
- **TODO/FIXME**：统一 `# TODO: xxx` / `# FIXME: xxx`。
- **禁止可变默认参数**：`list`/`dict` 默认用 `None` + 内部分支初始化。
- **单函数长度**：软约束 80 行，核心算法可 120 行，超了拆子函数。

## 数据模型选型

按运行时需求分层：
- API 请求/响应（schemas.py）：Pydantic `BaseModel`
- 内部数据结构（spots_dict、poi_cache）：`TypedDict`
- 跨模块业务对象（SpotDict/PlanResult）：`TypedDict`
- 配置/环境变量：Pydantic `BaseSettings`
- 命名：内部 `XxxDict`，API `XxxModel`

## NumPy / Numba 专项

- `dtype` 显式声明（`np.float64`，不用浮点字面量）。
- `njit` 只用于纯数值计算，不传 Python 对象。
- 矩阵维度语义全局统一：**行 = 出发节点，列 = 到达节点**。

## 数据单位全局约定

| 变量名 | 单位 | 说明 |
|--------|------|------|
| `dist_matrix` | km | 距离矩阵 |
| `cost_matrix` | 分钟 | 耗时矩阵（cost_matrix_hours * 60）|
| `travel_speed` | 无量纲 | `use_real_time_matrix=False` 时固定 1.0 |
| `use_real_time_matrix` | — | False=标准距离矩阵；True=高德真实时间矩阵 |
| `stay` | 分钟 | 景点停留时间 |
| `tw` | 分钟 | 时间窗 (start,end)，0-1440 |

## 接口清单（`__all__` 同步）

- 用 `__all__` 声明模块公开 API（替代手写清单），如 `__all__ = ["VNSSolver", "CASolver"]`。
- `__all__` 不得含下划线开头的私有函数。
- 新增公开 API：先更新 `__init__.py` 的 `__all__`，再跑 `tools/sync_all.py` 同步导出。

## 注释规范

- 段分隔线：`# ==== 段标题 ====`（主要）、`# ---- 子段 ----`（子）、`# ***** 标注 *****`（强调）。
- 对外关键函数用 Google 风格 docstring；已标注类型的参数省略参数类型，仅描述语义；`Returns` 含成本结构和取值范围。
- 内部方法单行 docstring。
- **Raises**：涉及外部输入必须在 docstring 标注可能异常。
- **行内注释**：传达 Why 而非 What（见对比案例）。

## 装饰器三态生命周期

`backend/utils/decorators.py` 三个标记装饰器，统一发 `UserWarning`：
- `@legacy_only`：已废弃、仅参考。确认无调用方且无保留价值 → 删。
- `@placeholder`：存在但暂不激活、去向未定。接入调用方或方向明确 → 改标/移除。
- `@refactor`：实现可用但需重构，方向写在 docstring 首行 `TODO(重构方向)`。重构完成 → 移除。

生命周期：新增标记（`@refactor` 必须写 `TODO(重构方向)`）→ 状态流转 → 里程碑 review 清点裁决。
