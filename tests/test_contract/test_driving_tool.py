"""driving 工具契约测试：get_driving 返回结构锁定。

不触网：monkeypatch 掉 _get_driving_data。
验证返回值携带起终点名（前端据此展示「A → B」）。
"""

from backend.agent.tools.driving.service import get_driving


def test_get_driving_includes_endpoint_names(monkeypatch):
    """成功路径返回含 origin_name / destination_name。"""
    monkeypatch.setattr(
        "backend.agent.tools.driving.service._get_driving_data",
        lambda origin, dest: (15.55, 2976.0, ""),
    )
    result = get_driving(
        {"name": "广州塔", "lon": 113.32, "lat": 23.1},
        {"name": "白云山", "lon": 113.3, "lat": 23.18},
    )
    assert result["origin_name"] == "广州塔"
    assert result["destination_name"] == "白云山"
    assert result["distance_km"] == 15.55
    assert result["duration_min"] == round(2976.0 / 60.0, 1)


def test_get_driving_failure_returns_error(monkeypatch):
    """失败路径返回含起终点名的 error。"""
    monkeypatch.setattr(
        "backend.agent.tools.driving.service._get_driving_data",
        lambda origin, dest: None,
    )
    result = get_driving(
        {"name": "A", "lon": 1, "lat": 1},
        {"name": "B", "lon": 2, "lat": 2},
    )
    assert "error" in result
    assert "A" in result["error"] and "B" in result["error"]
