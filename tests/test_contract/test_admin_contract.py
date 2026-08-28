"""管理员操作台契约测试：admin schemas 响应形状（纯单元，无 DB/Redis）。

覆盖轴5：AdminUser/AdminTask/AdminFeedback 字段契约；三个列表分页响应结构。
"""
from backend.api.schemas import (
    AdminFeedback,
    AdminFeedbackResponse,
    AdminTask,
    AdminTasksResponse,
    AdminUser,
    AdminUsersResponse,
)


class TestAdminUserContract:
    """用户列表项契约。"""

    def test_required_fields(self):
        u = AdminUser(
            id="u1", email="a@b.com", nickname="x", role="super_admin", is_active=True, created_at="2026-08-28"
        )
        assert u.role == "super_admin"
        assert u.is_active is True

    def test_optional_nullable(self):
        u = AdminUser(id="u1", role="user", is_active=True)
        assert u.email is None
        assert u.nickname is None
        assert u.created_at == ""


class TestAdminTaskContract:
    """任务列表项契约。"""

    def test_minimal(self):
        t = AdminTask(id="t1", task_type="plan", status="pending")
        assert t.task_type == "plan"
        assert t.status == "pending"
        assert t.finished_at is None


class TestAdminFeedbackContract:
    """反馈列表项契约。"""

    def test_minimal(self):
        f = AdminFeedback(id="f1", content="很好用")
        assert f.content == "很好用"
        assert f.rating is None


class TestAdminResponsesContract:
    """三个列表分页响应的结构契约。"""

    def test_users_response_shape(self):
        resp = AdminUsersResponse(
            items=[AdminUser(id="u1", role="user", is_active=True)], total=1, page=1, page_size=20
        )
        assert len(resp.items) == 1
        assert resp.total == 1

    def test_tasks_response_shape(self):
        resp = AdminTasksResponse(
            items=[AdminTask(id="t1", task_type="suggest", status="done")], total=1, page=1, page_size=20
        )
        assert resp.items[0].status == "done"

    def test_feedback_response_shape(self):
        resp = AdminFeedbackResponse(
            items=[AdminFeedback(id="f1", content="x")], total=1, page=1, page_size=20
        )
        assert resp.items[0].content == "x"
