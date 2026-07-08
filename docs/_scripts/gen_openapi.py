"""从 FastAPI 应用生成 openapi.json 快照供 Sphinx 文档站使用。"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.api.server import app

output = os.path.join(os.path.dirname(__file__), "..", "openapi.json")
with open(output, "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f, indent=2, ensure_ascii=False)
print(f"openapi.json 已生成: {os.path.abspath(output)}")
