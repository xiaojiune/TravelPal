"""组合根（Composition Root）：集中创建驾车数据提供者并供各应用层注入。

domain 只依赖端口（domain/ports.py 的 DrivingDataProvider），本模块是应用层
装配点——驾车数据实现的单一来源。换数据源（如高德→百度）只需改此文件，
各入口（tasks/executors、agent/tools/plan/{add,remove}）统一自此取，
消除分散的 `_driving = AmapDrivingProvider()` 硬编码重复。

说明：solver 走 infra/engine/solver 的注册表（get_solver）已是单点可插拔，
故本模块不再收敛；这里只承载「分散重复」的 DrivingDataProvider。
"""

from backend.infrastructure.auth.postgres_conversation_store import PostgresConversationStore
from backend.infrastructure.external.amap.driving_service import AmapDrivingProvider

# 单例：AmapDrivingProvider 无 volatile 状态（仅调高德 API + 共享缓存），多入口共享安全。
_driving_provider = AmapDrivingProvider()


def get_driving_provider():
    """返回驾车数据提供者单例（DrivingDataProvider 实现）。

    换数据源（如高德→百度）时改本文件实例化处即可，各入口零改动。
    """
    return _driving_provider


# 会话存储单例：PostgresConversationStore 无状态（历史用 checkpointer 单例；会话存取走传入的 session）。
_conversation_store = PostgresConversationStore()


def get_conversation_store():
    """返回会话存储单例（implements domain 会话端口 ConversationStore）。

    会话存取按请求注入 AsyncSession（经 SqlAlchemyConversationSession 适配），store 本身无状态。
    """
    return _conversation_store
