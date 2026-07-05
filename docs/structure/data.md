# 数据定义

## 单位约定

| 量 | 单位 |
|----|------|
| 距离 | 千米 (km) |
| 时间 | 小时 (h) |
| 速度 | 千米/小时 (km/h) |
| 经纬度 | 高德 GCJ-02 坐标系 |

## 核心数据结构

### cost_matrix_hours

```
np.ndarray, shape (N+1, N+1)
第 i→j 的旅行耗时（小时），0 索引为酒店/depot
```

### dist_matrix_km

```
np.ndarray, shape (N+1, N+1)
第 i→j 的行驶距离（千米），0 索引为酒店/depot
```

### spots_dict

```python
{
    idx: {
        "name": str,          # 景点名称
        "cost": float,        # 游玩耗时（小时）
        "tw": (float, float), # 时间窗 (start, end)，同为小时偏移量（0 为 08:00）
        "location": [lng, lat]  # 高德 GCJ-02 坐标
    }
}
```

### solution（单条路径）

```python
[int, int, ...]  # 节点序列，0 为酒店/depot，其他为景点索引
```

### group（分组方案）

```python
[
    [0, 3, 5, 7, 0],   # 第 1 天：酒店 → A → B → C → 酒店
    [0, 2, 4, 6, 0],   # 第 2 天：酒店 → D → E → F → 酒店
]
```

### analyze_solution 返回值

```python
Tuple[float, float, float, float, int]:
    cost = 距离 + 等待 + 迟到 + 惩罚（总成本）
    dist = 总行驶距离（km）
    wait_pen = 总等待时间（h）
    late_pen = 总迟到时间（h）
    violations = 违规节点数（0 表示完全可行）
```

## 数据集

TSPTW 测试集位于 `data/DataSets/`，命名格式 `n{节点数}w{时间窗宽度}`。每组含：
- `{name}.txt`：节点坐标 + 时间窗定义
- 用于算法性能测试和快慢模式基线对齐
