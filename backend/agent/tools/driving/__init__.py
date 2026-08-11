"""驾车路径工具子包：两点间驾车距离/耗时查询。

对应 TOOL_CATEGORIES 的 "driving" 分组。当前实现驾车（service.py），
未来扩展步行/骑行/公交路径时在本子包内新增实现，工具入口契约不变。
"""

from backend.agent.tools.driving.service import get_driving

__all__ = [
    "get_driving",
]
