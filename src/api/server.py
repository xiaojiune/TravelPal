from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import router


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。

    初始化 API 路由、CORS 跨域策略（允许 Vue 开发服务器访问）、
    静态资源挂载（CesiumJS /Build/ 目录）。

    Returns:
        FastAPI: 配置完成的应用实例。
    """
    app = FastAPI(title="TravelPal API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    # 挂载 CesiumJS 静态资源：Vue 页面中引用 /Build/Cesium.js 时可获取
    try:
        app.mount(
            "/Build",
            StaticFiles(directory="frontend/static/Cesium/Build"),
            name="cesium",
        )
    except RuntimeError:
        pass

    return app


def main():
    import uvicorn
    uvicorn.run("src.api.server:create_app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
