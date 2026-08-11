"""方案均衡功能：按可量化参数把景点在组间重分配，使各天该参数尽可能均衡。

定位：方案调整能力（planning 层），非求解器（engine）内部逻辑。当前为
占位（@placeholder）——原 pipeline.adjust_plan 的 {"balance": true} 指令分支
已删除，暂无调用方，待未来前端或 Agent 接线后再启用。

统一均衡函数：metric 决定衡量每日负荷的可量化参数——
- "stay"：停留时间（当前实现，景点点级属性可直接取值）
- "wait"：等待时间（后期扩展，需先求解再按路线统计每日等待）
- "dist"/"cost"：路程/成本均衡（同上，需求解感知，后期扩展）

扩展机制：metric 参数化 + 点负载函数分发。新增 metric 只需补充一个
「单点负载」计算函数并在 _LOAD_FUNCS 注册，分配算法复用。
"""

from typing import Callable

import numpy as np

from backend.typedefs import SpotDict
from backend.utils.decorators import placeholder

# 单点负载函数注册表：metric -> (spots, node) -> float
# 当前仅 stay（点级属性可直接算）；wait/dist/cost 需求解感知，后期按此扩展。
_LOAD_FUNCS: dict[str, Callable[[dict[int, SpotDict], int], float]] = {}


def _stay_load(spots: dict[int, SpotDict], node: int) -> float:
    """停留时间负载：取景点停留分钟数。"""
    return float(spots[node]["stay"])


_LOAD_FUNCS["stay"] = _stay_load


@placeholder
def balance_groups(
    groups: list,
    spots: dict[int, SpotDict],
    metric: str = "stay",
    cost_mat: np.ndarray | None = None,
    depot: int = 0,
) -> list:
    """把景点按指定 metric 贪心重分配到各天，使每日该参数负荷接近。

    排序策略：按单点负载降序，优先把大负载景点放入当前累计负荷最小的天，
    从而拉平各天总负荷。返回分组含首尾 depot（与 solve_groups 输入兼容）。

    Args:
        groups: 原始分组（不含 depot），每组为景点索引列表。
        spots: 景点字典，键为索引，值为含 stay 等属性的点。
        metric: 均衡的可量化参数，当前支持 "stay"；wait/dist/cost 预留。
        cost_mat: 成本矩阵（分钟）。wait/dist/cost 均衡时必需，当前未用。
        depot: depot 索引，默认 0。

    Returns:
        list: 均衡后的分组列表，每组含首尾 depot。

    Raises:
        ValueError: metric 未注册时抛出。
    """
    if metric not in _LOAD_FUNCS:
        raise ValueError(f"暂不支持的均衡参数 metric={metric}，可用: {sorted(_LOAD_FUNCS)}")
    load_fn = _LOAD_FUNCS[metric]

    # 汇总全部景点，按负载降序分配（大负载先放，利于拉平）
    all_spots = []
    seen: set[int] = set()
    for g in groups:
        for node in g:
            if node != depot and node not in seen:
                seen.add(node)
                all_spots.append(node)

    k = len(groups)
    new_groups: list[list[int]] = [[] for _ in range(k)]
    day_loads: list[float] = [0.0] * k

    for node in sorted(all_spots, key=lambda n: -load_fn(spots, n)):
        min_idx = int(min(range(k), key=lambda i: day_loads[i]))
        new_groups[min_idx].append(node)
        day_loads[min_idx] += load_fn(spots, node)

    balanced = [[depot] + core + [depot] for core in new_groups]
    final_loads = [sum(spots[n][metric] for n in g if n != depot) for g in balanced]
    print(f"  均衡后每日{metric}负荷: {final_loads}, 目标均值: {sum(final_loads) / k:.0f}")
    return balanced
