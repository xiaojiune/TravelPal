"""规划评语生成器：规则模板 + LLM 润色预留。

规则注册表 RULES 仅需在列表中添加函数，即可自动参与评语生成。
"""

import numpy as np


def check_wait(solution, spots, cost_mat):
    """等待惩罚超过阈值时提醒早到。"""
    wait = solution.get("wait", 0)
    if wait > 50:
        return f"总共有 {int(wait)} 分钟的等待时间，可以考虑晚点出门哦"
    return None


def check_late(solution, spots, cost_mat):
    """迟到惩罚超过阈值时提醒安排太满。"""
    late = solution.get("late", 0)
    if late > 50:
        return f"产生了 {int(late)} 分钟的迟到惩罚，当天的景点也许可以减掉一两个"
    return None


def check_density(solution, spots, cost_mat):
    """单日景点过多时提醒行程紧凑。"""
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
    """单日路程过长时提醒注意交通时间。"""
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
    """兜底：一切正常时给出正面评语。"""
    return "整体节奏适中，是个舒服的安排"


RULES = [check_wait, check_late, check_density, check_distance, check_normal]


def polish_with_llm(text: str, enabled: bool = False) -> str:
    # TODO: enabled=True 时调用 DeepSeek API 将评语润色为更口语化的表达
    return text


def generate_commentary(solution: dict, spots: dict, cost_mat: np.ndarray) -> str:
    """遍历规则注册表生成评语，取前两条非空结果拼接。

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
