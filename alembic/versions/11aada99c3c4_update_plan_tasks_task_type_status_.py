"""update plan_tasks task_type/status comments for or-ca/or-vns + canceled

Revision ID: 11aada99c3c4
Revises: 5de212be3a55
Create Date: 2026-08-31 13:52:08.625638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11aada99c3c4'
down_revision: Union[str, Sequence[str], None] = '5de212be3a55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """更新 plan_tasks 两列注释：task_type（or-ca/or-vns）、status（加 canceled）。

    对应端点语义化（or-ca/or-vns）与任务生命周期（canceled 终态）的列注释变更，
    models.py 声明已更新，此处同步数据库列注释以对齐。
    """
    op.alter_column(
        "plan_tasks",
        "task_type",
        existing_type=sa.String(length=16),
        existing_nullable=False,
        comment="任务类型：or-ca 或 or-vns",
    )
    op.alter_column(
        "plan_tasks",
        "status",
        existing_type=sa.String(length=16),
        existing_nullable=False,
        comment="pending/running/done/failed/canceled",
    )


def downgrade() -> None:
    """还原 plan_tasks 两列注释为旧值（suggest/plan、pending/running/done/failed）。"""
    op.alter_column(
        "plan_tasks",
        "task_type",
        existing_type=sa.String(length=16),
        existing_nullable=False,
        comment="任务类型：suggest 或 plan",
    )
    op.alter_column(
        "plan_tasks",
        "status",
        existing_type=sa.String(length=16),
        existing_nullable=False,
        comment="pending/running/done/failed",
    )
