"""create feedback_records

Revision ID: 3c7f2a91b5e8
Revises: 826d526fa614
Create Date: 2026-08-10 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c7f2a91b5e8"
down_revision: Union[str, Sequence[str], None] = "826d526fa614"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 feedback_records 表（与 backend/data/model/models.py 对齐）。"""
    op.create_table(
        "feedback_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=True, comment="可选：用户称呼"),
        sa.Column("contact", sa.String(200), nullable=True, comment="可选：联系方式（邮箱/微信等）"),
        sa.Column("content", sa.Text(), nullable=False, comment="反馈内容（必填）"),
        sa.Column("rating", sa.Integer(), nullable=True, comment="评分 1-5，可选"),
        sa.Column("page", sa.String(50), nullable=True, comment="来源页面路径，如 /about"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    """删除 feedback_records 表。"""
    op.drop_table("feedback_records")
