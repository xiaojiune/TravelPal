"""后端环境变量配置，通过 .env 文件或系统环境变量注入。"""

import os

from dotenv import load_dotenv

load_dotenv()

# 高德地图 Web 服务 API Key，用于后端 POI 搜索和驾车路径规划
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")
# 高德 Web 端 JS API Key，用于前端地图渲染
AMAP_JS_KEY = os.getenv("AMAP_JS_KEY", "")
# 高德 Web 端 JS API 安全密钥
AMAP_JS_SECURITY_CODE = os.getenv("AMAP_JS_SECURITY_CODE", "")
# LLM API Key，用于营业时间解析和 Agent 对话
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
# LLM API 基础地址，默认 DeepSeek
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
# LLM 模型名，默认 deepseek-chat
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
# PostgreSQL 数据库连接地址
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://travelpal:travelpal123@localhost:5432/travelpal")
# Embedding API Key（预留，当前未使用）
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
# Embedding 模型名（预留，当前未使用）
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
# Embedding API 基础地址（预留，当前未使用）
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "")
