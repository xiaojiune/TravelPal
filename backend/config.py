"""后端环境变量配置，通过 .env 文件或系统环境变量注入。

使用 pydantic-settings 集中管理：默认值 + 类型 + 校验（替代原 os.getenv 裸读）。
- 全局单例 `settings` 供各模块引用（`from backend.config import settings`）。
- `.env` 由 load_dotenv 注入 os.environ，pydantic 直接从环境读取，不依赖 cwd。
"""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """后端配置模型：环境变量集中定义，缺失时回落默认值。"""

    # 高德地图 Web 服务 API Key，用于后端 POI 搜索和驾车路径规划
    AMAP_API_KEY: str = ""
    # 高德 Web 端 JS API Key，用于前端地图渲染
    AMAP_JS_KEY: str = ""
    # 高德 Web 端 JS API 安全密钥
    AMAP_JS_SECURITY_CODE: str = ""
    # LLM API Key，用于营业时间解析和 Agent 对话
    LLM_API_KEY: str = ""
    # LLM API 基础地址，默认 DeepSeek
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    # LLM 模型名，默认 deepseek-chat
    LLM_MODEL: str = "deepseek-chat"
    # PostgreSQL 数据库连接地址
    DATABASE_URL: str = "postgresql+asyncpg://travelpal:travelpal123@localhost:5432/travelpal"
    # Celery 消息代理地址（redis），异步任务队列
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    # Redis 缓存地址（驾车成本点对缓存），默认与 broker 同实例
    REDIS_URL: str = "redis://localhost:6379/0"
    # Embedding API Key（预留，当前未使用）
    EMBEDDING_API_KEY: str = ""
    # Embedding 模型名（预留，当前未使用）
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    # Embedding API 基础地址（预留，当前未使用）
    EMBEDDING_BASE_URL: str = ""
    # 天气服务传输方式：http（基线）或 mcp（按需启用），配置级降级由 factory 读取
    WEATHER_TRANSPORT: str = "http"
    # Prometheus 多进程指标共享目录（backend 与 celery worker 必须指向同一目录才能聚合）
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp/travelpal_metrics"
    # uvicorn 开发热重载开关
    DEV_RELOAD: bool = False


settings = Settings()
