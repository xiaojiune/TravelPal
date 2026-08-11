"""create history_records

Revision ID: 8a3e69f118cd
Revises:
Create Date: 2026-08-02 17:55:29.161364

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a3e69f118cd"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 history_records 表（与 backend/data/model/models.py 对齐）。"""
    op.create_table(
        "history_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=True, comment="匿名设备标识，仅用于删除鉴权"),
        sa.Column("note", sa.Text(), nullable=True, comment="用户可选的备注"),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("hotel", sa.String(200), nullable=True),
        sa.Column("n_days", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("spot_count", sa.Integer(), nullable=True),
        sa.Column(
            "plan_result", JSONB(), nullable=False, comment="完整规划结果（routes/schedules/polylines/commentary 等）"
        ),
        sa.Column("request_params", JSONB(), nullable=True, comment="用户输入的请求参数"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_history_records_device_id", "history_records", ["device_id"], unique=False)


def downgrade() -> None:
    """删除 history_records 表。"""
    op.drop_index("ix_history_records_device_id", table_name="history_records")
    op.drop_table("history_records")
