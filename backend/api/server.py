"""FastAPI 应用工厂与启动入口。"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.data.model.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时创建数据库表，关闭时释放连接池。"""
    skip_db = os.getenv("SKIP_DB", "").lower() in ("1", "true")
    if not skip_db:
        await init_db()
    else:
        print("[SKIP_DB] 跳过数据库初始化，历史记录端点不可用")
    yield
    if not skip_db:
        await close_db()


# ================== 应用工厂 ==================


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    初始化 API 路由、CORS 跨域策略（允许 Vue 开发服务器访问）、
    数据库连接池、生命周期管理。

    Returns:
        FastAPI: 配置完成的应用实例。
    """
    app = FastAPI(title="TravelPal API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()

# ---------- 启动入口 ----------


def main():
    """启动 uvicorn 开发服务器，DEV_RELOAD 环境变量控制热重载。"""
    import uvicorn

    reload = os.getenv("DEV_RELOAD", "").lower() in ("1", "true")
    uvicorn.run("backend.api.server:app", host="0.0.0.0", port=8000, reload=reload)


if __name__ == "__main__":
    main()
