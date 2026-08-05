"""FastAPI 应用工厂与启动入口。"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from backend.api.routes import router
from backend.config import settings
from backend.data.model.database import close_db, init_db
from backend.observability import http_duration, http_requests, metrics_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时创建数据库表，关闭时释放连接池。

    Args:
        app: FastAPI 应用实例。

    Yields:
        None: 应用运行期间 yield，退出后执行关闭逻辑。
    """
    await init_db()
    yield
    await close_db()


# ================== HTTP 指标中间件 ==================


class MetricsMiddleware:
    """记录 HTTP 请求数（方法/路径/状态码）与耗时直方图。

    纯 ASGI 实现（不使用 BaseHTTPMiddleware），避免对流式响应
    （如 /api/chat SSE）的缓冲干扰；对 /api/metrics 自身路径跳过计数。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == "/api/metrics":
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "")
        start = time.monotonic()
        status = {"code": 0}

        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, wrapped_send)
        finally:
            http_requests.labels(method=method, path=path, status=str(status["code"])).inc()
            http_duration.labels(method=method, path=path).observe(time.monotonic() - start)


# ================== 应用工厂 ==================


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    初始化 API 路由、CORS 跨域策略（允许 Vue 开发服务器访问）、
    数据库连接池、生命周期管理、HTTP 观测性中间件与 /api/metrics 端点。

    Returns:
        FastAPI: 配置完成的应用实例。
    """
    app = FastAPI(title="TravelPal API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/metrics")
    async def metrics():
        """Prometheus 指标端点：聚合 backend 与 celery worker 全部进程指标。

        Returns:
            Response: Prometheus 文本格式指标（Content-Type: text/plain; version=0.0.4）。
        """
        content_type, body = metrics_response()
        return Response(content=body, media_type=content_type)

    app.include_router(router)

    return app


app = create_app()

# ---------- 启动入口 ----------


def main():
    """启动 uvicorn 开发服务器，DEV_RELOAD 环境变量控制热重载。"""
    import uvicorn

    reload = settings.DEV_RELOAD
    uvicorn.run("backend.api.server:app", host="0.0.0.0", port=8000, reload=reload)


if __name__ == "__main__":
    main()
