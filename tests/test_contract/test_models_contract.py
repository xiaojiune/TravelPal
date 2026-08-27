"""数据模型契约测试：纯 SQLAlchemy metadata 断言，不连数据库，防字段/外键漂移。

覆盖轴2：User 模型字段齐全；三张业务表均挂 user_id 外键（可空=存量匿名兼容）。
"""
from backend.data.model.models import FeedbackRecord, HistoryRecord, PlanTask, User


class TestUserModel:
    """User 模型字段契约。"""

    def test_required_columns(self):
        cols = set(User.__table__.c.keys())
        for name in (
            "id",
            "role",
            "email",
            "password_hash",
            "nickname",
            "is_active",
            "created_at",
            "updated_at",
        ):
            assert name in cols, f"users 表缺列 {name}"


class TestBusinessUserIdForeignKey:
    """三张业务表的 user_id 外键与可空契约（存量匿名记录兼容）。"""

    def test_user_id_column_nullable_and_fk(self):
        for model in (HistoryRecord, PlanTask, FeedbackRecord):
            col = model.__table__.c.user_id
            assert col.nullable is True, f"{model.__tablename__}.user_id 应为可空"
            assert len(col.foreign_keys) == 1, f"{model.__tablename__}.user_id 应有 1 个外键"
            fk_target = next(iter(col.foreign_keys)).column
            assert (fk_target.table.name, fk_target.name) == ("users", "id"), (
                f"{model.__tablename__}.user_id 外键应指向 users.id"
            )
