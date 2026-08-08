"""规划评语生成器：规则模板 + LLM 润色预留（agent-tool 形态）。

评语已从规划/调整流程剥离（规划结果不再自动附评语），generate_commentary
转为 Agent 工具形态待接入（@placeholder）。规则注册表 RULES 仅需在列表中
添加函数，即可自动参与评语生成。
"""

import numpy as np

from backend.utils.decorators import placeholder

# ================== 规则模板 ==================

# ---------- 子规则 ----------


def check_wait(solution, spots, cost_mat):
    """等待惩罚超过阈值时提醒早到。

    Args:
        solution: 求解结果，含 wait/late/routes 等。
        spots: 景点字典。
        cost_mat: 距离矩阵（km）。

    Returns:
        str | None: 超过 50 分钟等待时返回提醒文本，否则 None。
    """
    wait = solution.get("wait", 0)
    if wait > 50:
        return f"总共有 {int(wait)} 分钟的等待时间，可以考虑晚点出门哦"
    return None


def check_late(solution, spots, cost_mat):
    """迟到惩罚超过阈值时提醒安排太满。

    Args:
        solution: 求解结果。
        spots: 景点字典。
        cost_mat: 距离矩阵。

    Returns:
        str | None: 超过 50 分钟迟到惩罚时返回提醒文本，否则 None。
    """
    late = solution.get("late", 0)
    if late > 50:
        return f"产生了 {int(late)} 分钟的迟到惩罚，当天的景点也许可以减掉一两个"
    return None


def check_density(solution, spots, cost_mat):
    """单日景点过多时提醒行程紧凑。

    Args:
        solution: 求解结果，含 routes 路径列表。
        spots: 景点字典。
        cost_mat: 距离矩阵。

    Returns:
        str | None: 存在超过 5 个景点的天数时返回提醒，否则 None。
    """
    max_per_day = 5
    triggered = []
    for di, route in enumerate(solution["routes"]):
        spot_count = sum(1 for n in route if n != 0)
        if spot_count > max_per_day:
            triggered.append((di + 1, spot_count))
    if triggered:
        parts = [f"第{d}天安排了{c}个景点，会比较赶" for d, c in triggered]
        return "；".join(parts)
    return None


def check_distance(solution, spots, cost_mat):
    """单日路程过长时提醒注意交通时间。

    Args:
        solution: 求解结果，含 routes 路径列表。
        spots: 景点字典。
        cost_mat: 距离矩阵（km）。

    Returns:
        str | None: 存在超过 50km 的天数时返回提醒，否则 None。
    """
    threshold_km = 50
    triggered = []
    for di, route in enumerate(solution["routes"]):
        day_dist = sum(cost_mat[route[i]][route[i + 1]] for i in range(len(route) - 1))
        if day_dist > threshold_km:
            triggered.append((di + 1, int(day_dist)))
    if triggered:
        parts = [f"第{d}天总路程约{c}公里，交通时间较长" for d, c in triggered]
        return "；".join(parts)
    return None


def check_normal(solution, spots, cost_mat):
    """兜底：一切正常时给出正面评语。

    Args:
        solution: 求解结果。
        spots: 景点字典。
        cost_mat: 距离矩阵。

    Returns:
        str: 固定正面评语。
    """
    return "整体节奏适中，是个舒服的安排"


RULES = [check_wait, check_late, check_density, check_distance, check_normal]


# ================== LLM 润色 ==================


def polish_with_llm(text: str, enabled: bool = False) -> str:
    """LLM 润色评语（预留）。

    Args:
        text: 原始评语文本。
        enabled: 是否启用 LLM 润色，默认关闭。

    Returns:
        str: 原文本（润色功能暂未实现）。
    """
    return text


@placeholder
def generate_commentary(solution: dict, spots: dict, cost_mat: np.ndarray) -> str:
    """遍历规则注册表生成评语，取前两条非空结果拼接。

    TODO(重构方向)：评语已从 run_planning / adjust_plan 流程剥离（返回
    commentary=None），本函数转为 Agent 工具形态——后期经 orchestrator 注册
    为工具（TOOL_REGISTRY），由 Agent 决定是否生成评语，并接入 LLM 润色。

    Args:
        solution: solve_groups 返回的结果，含 routes/total_cost/wait/late 等。
        spots: 景点字典。
        cost_mat: 距离矩阵（km）。

    Returns:
        拼接后的评语文本。
    """
    parts = []
    for rule in RULES:
        result = rule(solution, spots, cost_mat)
        if result:
            parts.append(result)
        if len(parts) >= 2:
            break
    text = "。".join(parts)
    return polish_with_llm(text)
