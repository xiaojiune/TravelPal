"""api 层契约测试：锁定 schemas Pydantic 模型契约。

ADR-010 #7（契约测试）：纯单元验证 backend/api/schemas.py 的请求/响应模型，
防止字段演进（重命名/类型变更/必填调整）时静默破坏前后端契约：
- PlanRequest 必填字段 / 默认值 / 校验约束（mode/day_start 范围）
- TaskSubmitResponse / TaskDetail 形状（前端轮询依赖）
- SuggestResult / PlanResult 响应形状
- FeedbackCreate 形状（/about 问卷提交依赖）

不启 TestClient（避免触网/依赖 DB），纯 Pydantic 验证。
"""

import pytest

from backend.api.schemas import (
    FeedbackCreate,
    PlanRequest,
    SuggestionItem,
    SuggestResult,
    TaskDetail,
    TaskSubmitResponse,
)


def _valid_plan_payload() -> dict:
    """构造一份合法的 PlanRequest 载荷。"""
    return {
        "city": "广州",
        "hotel_name": "广州酒店",
        "hotel_lon": 113.3,
        "hotel_lat": 23.1,
        "spots": [
            {
                "name": "广州塔",
                "lon": 113.32,
                "lat": 23.1,
                "tw_start": 570,
                "tw_end": 1350,
                "stay": 180,
            }
        ],
    }


class TestPlanRequestContract:
    """请求模型契约。"""

    def test_required_fields(self):
        for field in ("city", "hotel_name", "hotel_lon", "hotel_lat", "spots"):
            payload = _valid_plan_payload()
            del payload[field]
            with pytest.raises(ValueError):
                PlanRequest(**payload)

    def test_defaults(self):
        req = PlanRequest(**_valid_plan_payload())
        assert req.mode == "fast"
        assert req.day_start == 0
        assert req.penalty_weight == 100.0
        assert req.early_wait_weight == 0.1
        assert req.late_return_weight == 50.0
        assert req.n_days is None
        assert req.min_days is None

    def test_spots_min_length_one(self):
        payload = _valid_plan_payload()
        payload["spots"] = []
        with pytest.raises(ValueError):
            PlanRequest(**payload)

    def test_mode_enum(self):
        payload = _valid_plan_payload()
        payload["mode"] = "bogus"
        with pytest.raises(ValueError):
            PlanRequest(**payload)

    def test_day_start_range(self):
        payload = _valid_plan_payload()
        payload["day_start"] = 2000
        with pytest.raises(ValueError):
            PlanRequest(**payload)


class TestTaskResponseContract:
    """任务响应模型契约（前端轮询依赖）。"""

    def test_task_submit_response_shape(self):
        resp = TaskSubmitResponse(task_id="abc-123")
        assert resp.task_id == "abc-123"

    def test_task_detail_shape(self):
        detail = TaskDetail(task_id="abc-123", task_type="plan", status="done")
        assert detail.result is None
        assert detail.error is None

    def test_task_detail_result_optional(self):
        detail = TaskDetail(task_id="abc", task_type="plan", status="done", result=None, error="boom")
        assert detail.status == "done"
        assert detail.error == "boom"


class TestSuggestResultContract:
    """建议响应形状契约。"""

    def _sample_item(self) -> dict:
        return {
            "n_days": 2,
            "method": "K-means",
            "cost": 300.0,
            "total_dist": 120.0,
            "wait": 10.0,
            "late": 0.0,
            "routes": [[0, 1, 0]],
        }

    def test_suggestion_item_minimal(self):
        item = SuggestionItem(**_valid_item())
        assert item.n_days == 2

    def test_suggest_result_shape(self):
        result = SuggestResult(
            suggestions=[SuggestionItem(**_valid_item())],
            algo_time=3.5,
            spots={},
            cost_matrix=[],
            dist_matrix=[],
            polylines={},
            amap_api_key="k",
            amap_security_code="c",
        )
        assert result.type == "suggestion"


class TestFeedbackCreateContract:
    """用户反馈请求模型契约（/about 问卷提交依赖）。"""

    def test_content_required(self):
        with pytest.raises(ValueError):
            FeedbackCreate(content="")

    def test_optional_fields(self):
        fb = FeedbackCreate(content="很好用", name="张三", contact="a@b.com", rating=4, page="/about")
        assert fb.name == "张三"
        assert fb.rating == 4
        assert fb.page == "/about"

    def test_minimal_content_only(self):
        fb = FeedbackCreate(content="很好用")
        assert fb.name is None
        assert fb.contact is None
        assert fb.rating is None
        assert fb.page is None

    def test_rating_range(self):
        for bad in (0, 6):
            with pytest.raises(ValueError):
                FeedbackCreate(content="x", rating=bad)

    def test_content_max_length(self):
        with pytest.raises(ValueError):
            FeedbackCreate(content="长" * 2001)


def _valid_item() -> dict:
    return {
        "n_days": 2,
        "method": "K-means",
        "cost": 300.0,
        "total_dist": 120.0,
        "wait": 10.0,
        "late": 0.0,
        "routes": [[0, 1, 0]],
    }
