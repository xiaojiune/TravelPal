"""SQLAlchemy ORM 模型定义。"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from backend.data.model.database import Base


class HistoryRecord(Base):
    __tablename__ = "history_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(64), nullable=True, index=True, comment="匿名设备标识，仅用于删除鉴权")
    note = Column(Text, nullable=True, comment="用户可选的备注")
    city = Column(String(100), nullable=False)
    hotel = Column(String(200), nullable=True)
    n_days = Column(Integer, nullable=False)
    cost = Column(Float, nullable=True)
    spot_count = Column(Integer, nullable=True)
    plan_result = Column(JSONB, nullable=False, comment="完整规划结果（routes/schedules/polylines/commentary 等）")
    request_params = Column(JSONB, nullable=True, comment="用户输入的请求参数")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
