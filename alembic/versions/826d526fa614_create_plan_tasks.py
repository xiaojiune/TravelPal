"""create plan_tasks

Revision ID: 826d526fa614
Revises: 8a3e69f118cd
Create Date: 2026-08-04 00:35:13.781315

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "826d526fa614"
down_revision: Union[str, Sequence[str], None] = "8a3e69f118cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 plan_tasks 表（与 backend/data/model/models.py 对齐）。"""
    op.create_table(
        "plan_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("task_type", sa.String(16), nullable=False, comment="任务类型：suggest 或 plan"),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="pending",
            comment="pending/running/done/failed",
        ),
        sa.Column("request_params", JSONB(), nullable=False, comment="提交的完整请求参数（PlanRequest 结构）"),
        sa.Column("result", JSONB(), nullable=True, comment="成功结果（suggest 完整响应或完整 PlanResult）"),
        sa.Column("error", sa.Text(), nullable=True, comment="失败错误信息"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="任务开始执行时间"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="任务结束时间（成功或失败）"),
    )


def downgrade() -> None:
    """删除 plan_tasks 表。"""
    op.drop_table("plan_tasks")
