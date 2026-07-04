# src/api/__init__.py
#
# ================== 接口清单 ==================
#
# ---- server.py ----
# create_app() -> FastAPI                                创建并配置 FastAPI 应用实例
# main() -> None                                         启动 uvicorn 开发服务器
#
# ---- routes.py ----
# POST /api/poi-lookup                                   批量查询 POI 坐标和地址
# POST /api/suggest                                      调用 run_planning(n_days=None) 返回方案建议列表
# POST /api/plan                                         调用 run_planning(n_days=...) 返回完整方案
# POST /api/chat                                         预留 LLM Agent 对话接口（当前返回未实现）
#
# ---- schemas.py ----
# PlanRequest(BaseModel)                                 统一请求模型：酒店 + 景点 + 算法参数
# POIItem(BaseModel)                                     单个景点数据：名称、坐标、时间窗、停留时长
# POILookupRequest(BaseModel)                            POI 坐标/地址查询请求
# POILookupItem(BaseModel)                               单个 POI 查询结果
# POILookupResponse(BaseModel)                           POI 查询响应

from src.api.server import create_app

__all__: list[str] = ["create_app"]
