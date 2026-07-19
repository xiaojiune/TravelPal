"""SQLAlchemy ORM 模型定义。"""

import uuid

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from backend.data.model.database import Base


class HistoryRecord(Base):
    """历史记录 ORM 模型，存储完整规划结果至 PostgreSQL。

    设计说明：
    - plan_result 使用 JSONB 而非关系化展开——前端展示「分享站」时按 ID 整条读取，
      无需对 plan 内容做字段级查询；全量 JSONB 写入简单，读取仅一次，适合此场景。
    - 单条 plan_result 体积可达数百 KB（含 polylines/cost_matrix），
      分页列表只返回摘要字段（id/city/n_days/cost 等），不加载 JSONB 列。
    - device_id 由前端 localStorage 自动生成，仅用于删除鉴权——软鉴权设计，
      不引入真实用户系统，对访客零门槛。
    """
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
