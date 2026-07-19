"""Async SQLAlchemy 引擎与会话管理。"""

import os

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config import DATABASE_URL

SKIP_DB = os.getenv("SKIP_DB", "").lower() in ("1", "true")

# 引擎配置说明：
# - pool_size=5：连接池最小保持连接数，PostgreSQL 默认 max_connections=100，
#   单 TravelPal 实例 5 个连接足够（请求短且无长事务）
# - max_overflow=10：突发流量时最多临时创建 10 个额外连接，总计 15 个
# - echo=False：关闭 SQL 日志，生产环境可开启调试
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 声明式基类，所有数据模型继承此类。"""


async def get_session() -> AsyncSession:
    """获取异步数据库会话，用于 FastAPI Depends 注入。"""
    if SKIP_DB:
        raise HTTPException(status_code=503, detail="数据库未启用（SKIP_DB 模式）")
    async with async_session() as session:
        yield session


async def init_db():
    """创建所有 ORM 模型对应的数据库表（幂等，CREATE TABLE IF NOT EXISTS）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接池，释放所有连接。"""
    await engine.dispose()
