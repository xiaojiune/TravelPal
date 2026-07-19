"""FastAPI HTTP 接口层：路由注册、请求模型（schemas）、服务端配置（server）。"""

from backend.api.server import create_app

__all__ = [
    "create_app",
]
