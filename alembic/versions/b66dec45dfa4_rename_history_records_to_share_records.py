"""rename history_records to share_records

Revision ID: b66dec45dfa4
Revises: 30d2fa80d5e2
Create Date: 2026-08-27 23:51:39.593017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b66dec45dfa4'
down_revision: Union[str, Sequence[str], None] = '30d2fa80d5e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("history_records", "share_records")
    op.execute("ALTER INDEX ix_history_records_device_id RENAME TO ix_share_records_device_id")
    op.execute("ALTER INDEX ix_history_records_user_id RENAME TO ix_share_records_user_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER INDEX ix_share_records_device_id RENAME TO ix_history_records_device_id")
    op.execute("ALTER INDEX ix_share_records_user_id RENAME TO ix_history_records_user_id")
    op.rename_table("share_records", "history_records")
