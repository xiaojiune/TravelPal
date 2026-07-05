# 后端结构

## 目录结构

```
backend/
├── config.py                   # 环境变量读取入口（AMap Key、模型参数等）
├── engine/                     # 求解核心
│   ├── ca.py                   CASolver：压缩退火主循环 + 邻域 + 2-opt
│   ├── vns.py                  VNSSolver：Shake → VND → SA 接收 + 精英池
│   ├── clustering.py           6 种聚类方法注册表
│   ├── fitness.py              适应度计算（距离 + 等待 + 迟到 + 晚归惩罚）
│   ├── search.py               ca_suggest() + cluster_and_solve() + solve_groups()
│   └── pipeline.py             run_planning()：流程编排
│
├── api/                        # HTTP 接口
│   ├── server.py               FastAPI 应用入口
│   ├── routes.py               /api/suggest / /api/plan / /api/chat
│   └── schemas.py              Pydantic 请求/响应模型
│
├── agent/                      # LLM Agent
│   ├── planner.py              行程调整 / 推荐
│   ├── commentator.py          方案评语生成
│   └── tools.py                工具函数
│
└── data/                       # 数据层
    ├── amap_loader.py          build_real_data()：高德 API → 成本矩阵
    ├── knowledge_base.py       知识库检索
    └── chroma_db/              向量数据库（待填充）
```

## 模块职责

| 模块 | 定位 | 关键函数 |
|------|------|---------|
| `ca.py` | 快速求解器 | `CASolver.solve()` |
| `vns.py` | 深度求解器 | `VNSSolver.solve()` |
| `clustering.py` | 分组策略 | `call_cluster()` |
| `fitness.py` | 成本计算 | `analyze_solution()` |
| `search.py` | 编排入口 | `ca_suggest()` / `cluster_and_solve()` / `solve_groups()` |
| `pipeline.py` | 流程编排 | `run_planning()` |

## 引擎级调用链路

```
run_planning(poi_cache, city, hotel_name, penalty_weight, early_wait_weight, late_return_weight, mode, n_days)
  │
  ├── build_real_data()              高德 API → 成本矩阵
  │
  ├── cluster_and_solve(spots, depot, dist_mat, mode, n_days)
  │     │
  │     ├── ca_suggest()             未指定天数 → 返回 top-5 建议
  │     │     ├── 遍历聚类方法 × n_days
  │     │     ├── 增益阈值早退（<1.0% × 3 次 → stop）
  │     │     ├── 去重 + 排序取 top-5
  │     │     └── 返回 {"type": "suggestion"}
  │     │
  │     └── 指定天数
  │           ├── 遍历 6 种聚类方法
  │           ├── solve_groups(solver_type="CA"/"VNS")
  │           └── 返回 {"type": "solution"}
  │
  └── type="suggestion" → 返回给用户，等待指定 n_days
      type="solution"
        ├── 生成每日行程（时间窗收缩 + 到达状态判断）
        └── 返回完整结果（含 spots、routes，供前端 AMap 可视化）
```
