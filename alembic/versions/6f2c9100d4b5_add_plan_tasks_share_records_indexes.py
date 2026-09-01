"""add indexes for plan_tasks (user_id,created_at)+(created_at), share_records.created_at; drop redundant user_id

Revision ID: 6f2c9100d4b5
Revises: 11aada99c3c4
Create Date: 2026-09-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6f2c9100d4b5"
down_revision: Union[str, Sequence[str], None] = "11aada99c3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 plan_tasks / share_records 补索引，服务两类热查询；并删除冗余单列索引。

    - plan_tasks: 用户任务面板 `WHERE user_id=? ORDER BY created_at DESC`（复合索引）
      + admin 全量任务列表 `ORDER BY created_at DESC`（无 user 过滤，复合不命中，需单列）。
    - share_records: 分享站列表 `ORDER BY created_at DESC`（单列索引）。
    - 删除 `ix_plan_tasks_user_id`：新增的 `(user_id, created_at)` 复合索引左前缀已覆盖
      `WHERE user_id=?`，原单列索引冗余，去之减少写放大。
    注：users/feedback_records 本轮不建（低频小表，保持克制）。
    """
    op.drop_index("ix_plan_tasks_user_id", table_name="plan_tasks")
    op.create_index("ix_plan_tasks_user_created", "plan_tasks", ["user_id", "created_at"], postgresql_using="btree")
    op.create_index("ix_plan_tasks_created_at", "plan_tasks", ["created_at"], postgresql_using="btree")
    op.create_index("ix_share_records_created_at", "share_records", ["created_at"], postgresql_using="btree")


def downgrade() -> None:
    """回滚：删除本轮新增索引，并恢复被删的 plan_tasks.user_id 单列索引。"""
    op.drop_index("ix_plan_tasks_user_created", table_name="plan_tasks")
    op.drop_index("ix_plan_tasks_created_at", table_name="plan_tasks")
    op.drop_index("ix_share_records_created_at", table_name="share_records")
    op.create_index("ix_plan_tasks_user_id", "plan_tasks", ["user_id"], postgresql_using="btree")
