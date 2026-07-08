"""使用 FastAPI TestClient 导出 OpenAPI 规范 JSON。

不启动服务器即生成 openapi.json，供 openapi-typescript 等前端工具使用。

用法:
    python -m backend.tools.gen_openapi
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient
from backend.api.server import app


def main():
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    output = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"
    output.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"openapi.json 已生成: {output}")


if __name__ == "__main__":
    main()
