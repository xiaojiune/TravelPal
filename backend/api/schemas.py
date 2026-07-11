"""Pydantic 请求/响应模型定义，FastAPI 自动据此生成 OpenAPI 文档。"""

from pydantic import BaseModel, Field


class POIItem(BaseModel):
    """单个景点数据模型。

    Attributes:
        name: 景点名称（用于显示和 API 查询）。
        lon: 经度（GCJ-02 坐标系，与高德 API 一致）。
        lat: 纬度。
        tw_start: 时间窗开始，距午夜分钟数（默认 480 = 8:00）。
        tw_end: 时间窗结束，距午夜分钟数（默认 1020 = 17:00）。
        stay: 建议停留时长（分钟），影响时间窗有效结束时间。
        expected_arrival: 用户期望到达时间，可为空。
    """
    name: str
    lon: float
    lat: float
    tw_start: float = Field(default=480, description="营业开始时间，距午夜分钟数")
    tw_end: float = Field(default=1020, description="营业结束时间，距午夜分钟数")
    stay: float = Field(default=0, description="停留时间，分钟")
    expected_arrival: float | None = Field(default=None, description="预期到达时间，距午夜分钟数")


# ================== 查询请求 / 响应 ==================


class POILookupRequest(BaseModel):
    """POI 坐标/地址查询请求。

    调用高德 POI 搜索 API 批量获取坐标和地址。
    酒店也作为普通 POI 查询，前端根据名称匹配区分。
    """
    city: str
    names: list[str] = Field(min_length=1, description="POI 名称列表（酒店+景点）")


class POILookupItem(BaseModel):
    """单个 POI 查询结果。

    tw_start/tw_end 由 LLM 解析 opentime2 后返回，
    前端不再硬编码默认营业时间。
    """
    name: str
    lon: float
    lat: float
    address: str
    tw_start: int | None = Field(default=None, description="营业开始分钟数，0-1440，LLM 解析")
    tw_end: int | None = Field(default=None, description="营业结束分钟数，0-1440，LLM 解析")


class POILookupResponse(BaseModel):
    """POI 查询响应。

    items: 查询成功的 POI 列表。
    failed: 未找到的 POI 名称列表。
    """
    items: list[POILookupItem]
    failed: list[str]


# ================== 规划请求 ==================


class PlanRequest(BaseModel):
    """统一请求模型，适用于 /api/suggest 和 /api/plan。

    包含酒店信息、景点列表和算法参数。
    n_days 为 None 时返回方案建议（ca_suggest），否则返回完整方案。

    Attributes:
        city: 城市名（用于文件命名和显示）。
        hotel_name: 酒店名称。
        hotel_lon/lat: 酒店坐标（GCJ-02）。
        hotel_tw_start/end: 酒店时间窗（默认 0:00~24:00）。
        spots: 景点列表，至少 1 个。
        min_days: 搜索最小天数（默认由引擎自动推断，n_spots//8+1）。
        n_days: 行程天数。None 时走建议模式，有值时走规划模式。
        mode: "fast"(CA) 或 "deep"(VNS)。
        day_start: 一天启程时间，对所有景点生效（默认 0 = 午夜）。
        penalty_weight: 迟到惩罚权重。
        early_wait_weight: 早到等待惩罚权重。
        late_return_weight: 晚归惩罚权重。
    """
    city: str
    hotel_name: str
    hotel_lon: float
    hotel_lat: float
    hotel_tw_start: float = Field(default=0, ge=0, le=1440,
                                   description="酒店开放时间开始，距午夜分钟数（默认 0 = 全天）")
    hotel_tw_end: float = Field(default=1440, ge=0, le=1440,
                                 description="酒店开放时间结束，距午夜分钟数（默认 1440 = 24:00）")
    min_days: int | None = Field(default=None, description="搜索最小天数，不传则由引擎自动推断 (n_spots//8+1)")
    spots: list[POIItem] = Field(min_length=1, description="景点列表，至少 1 个")
    n_days: int | None = Field(default=None, description="行程天数，None 时返回建议")
    mode: str = Field(default="fast", pattern="^(fast|deep)$",
                      description="求解模式：fast(CA) 或 deep(VNS)")
    day_start: float = Field(default=0, ge=0, le=1440,
                              description="一天启程时间（距午夜分钟数），0=午夜")
    penalty_weight: float = Field(default=100.0, ge=0,
                                  description="迟到惩罚权重（默认 100.0）")
    early_wait_weight: float = Field(default=0.1, ge=0,
                                     description="早到等待惩罚权重（默认 0.1）")
    late_return_weight: float = Field(default=50.0, ge=0,
                                      description="晚归惩罚权重（默认 50.0）")


# ================== Agent 对话 ==================


class ChatRequest(BaseModel):
    """LLM Agent 对话请求。

    message: 用户输入的消息。
    plan_result: 可选的规划结果上下文，供 Agent 参考。
    """
    message: str = Field(min_length=1, description="用户输入的消息")
    plan_result: dict | None = Field(default=None, description="规划结果上下文")


# ================== 方案调整 ==================


class PlanAdjustRequest(BaseModel):
    """方案调整请求。

    前端在查看方案后希望调整（如均衡天、改天数、移除/添加景点）时调用。
    支持 balance / adjust_days / remove_poi / add_poi。
    """
    spots: dict
    cost_matrix: list
    dist_matrix: list
    routes: list
    adjustments: dict = Field(default_factory=lambda: {"balance": True},
                               description="调整指令，如 {'balance': true}")
