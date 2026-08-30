"""SQLAlchemy ORM 模型定义。"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from backend.data.model.database import Base


class User(Base):
    """用户 ORM 模型：实名账号 + 匿名访客（role=guest）。

    设计说明：
    - role：user（实名）/ guest（匿名访客，无密码）/ admin（管理员）。
    - user_id 是业务数据（history/plan_tasks/feedback）的唯一归属键。
    - 匿名访客首次访问由鉴权层生成 guest 记录，登录后可升级/合并为实名 user。
    - email/password_hash 对 guest 为 NULL。
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(String(16), nullable=False, default="user", comment="user/guest/admin")
    email = Column(String(255), nullable=True, comment="登录邮箱（guest 为 NULL）")
    password_hash = Column(String(255), nullable=True, comment="密码哈希（guest 为 NULL）")
    nickname = Column(String(100), nullable=True, comment="昵称")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SharedPlan(Base):
    """方案分享 ORM 模型，存储分享的规划结果至 PostgreSQL。

    设计说明：
    - plan_result 使用 JSONB 而非关系化展开——前端展示「分享站」时按 ID 整条读取，
      无需对 plan 内容做字段级查询；全量 JSONB 写入简单，读取仅一次，适合此场景。
    - 单条 plan_result 体积可达数百 KB（含 polylines/cost_matrix），
      分页列表只返回摘要字段（id/city/n_days/cost 等），不加载 JSONB 列。
    - device_id 由前端 localStorage 自动生成，仅用于删除鉴权——软鉴权设计，
      不引入真实用户系统，对访客零门槛。
    """

    __tablename__ = "share_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="归属用户（可空=存量匿名；单一归属键）",
    )
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


class PlanTask(Base):
    """异步规划任务 ORM 模型，存储 or-ca/or-vns 任务的执行状态与结果。

    设计说明：
    - 前端不再同步等待长耗时规划（suggest 拉取驾车 API 成本矩阵可达 40s），
      改为提交任务后轮询本表状态，避免 HTTP 长连接挂起。
    - 任务执行由 Celery worker 承担（broker=LavinMQ/AMQP），任务内部自写本表状态
      （方案 A：不依赖 Celery result backend，复用现有 async SQLAlchemy）。
    - result 存完整结果 JSONB（suggest 响应或完整 PlanResult），与 SharedPlan
      的 plan_result 同构；删除由用户主动发起，暂不做软删除/归档。
    - task_type 区分 "or-ca"（CA 建议）与 "or-vns"（指定天数求解），
      未来 OR+AI/ML 架构演进时可为不同类型任务配置不同队列/worker。
    """

    __tablename__ = "plan_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True, comment="归属用户（可空）")
    task_type = Column(String(16), nullable=False, comment="任务类型：or-ca 或 or-vns")
    status = Column(String(16), nullable=False, default="pending", comment="pending/running/done/failed/canceled")
    request_params = Column(JSONB, nullable=False, comment="提交的完整请求参数（PlanRequest 结构）")
    result = Column(JSONB, nullable=True, comment="成功结果（suggest 完整响应或完整 PlanResult）")
    error = Column(Text, nullable=True, comment="失败错误信息")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True, comment="任务开始执行时间")
    finished_at = Column(DateTime(timezone=True), nullable=True, comment="任务结束时间（成功或失败）")


class FeedbackRecord(Base):
    """用户反馈 ORM 模型，收集 /about 页面问卷提交。

    设计说明：
    - 问卷固定在 /about 页面，page 字段记录来源页面（接受恒为 /about），
      为将来在其它页面复用问卷预留扩展位。
    - name/contact 可选——降低填写门槛，内容(content)为唯一必填字段。
    - rating 1-5 整数评分，可选，用于快速量化满意度。
    """

    __tablename__ = "feedback_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True, comment="归属用户（可空）")
    name = Column(String(100), nullable=True, comment="可选：用户称呼")
    contact = Column(String(200), nullable=True, comment="可选：联系方式（邮箱/微信等）")
    content = Column(Text, nullable=False, comment="反馈内容（必填）")
    rating = Column(Integer, nullable=True, comment="评分 1-5，可选")
    page = Column(String(50), nullable=True, comment="来源页面路径，如 /about")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Conversation(Base):
    """会话 ORM 模型：对话持久化的元数据（thread_id 绑定、归属、TTL）。

    设计说明：
    - id 即 LangGraph 的 thread_id：会话状态（含消息历史）由 AsyncPostgresSaver
      托管在 checkpoint 表，本表只存会话元数据，避免双份存储（单一来源）。
    - user_id 可空：登录用户绑定账号（跨设备可查），未登录访客为 None（匿名）。
    - expires_at 是清理依据（登录 7 天/匿名 1 天），过期由清理逻辑删除本记录
      并同步清理对应 checkpoint 状态。
    """

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="归属用户（可空=匿名）",
    )
    title = Column(String(200), nullable=True, comment="会话标题（可选，如首条消息摘要）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True, comment="过期时间（登录7天/匿名1天）")
