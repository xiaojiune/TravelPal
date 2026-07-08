import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

project = "TravelPal"
copyright = "2026, xiaojiune"
author = "xiaojiune"
release = "0.1.0"

extensions = [
    "myst_parser",
    "autoapi",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", ".DS_Store"]

language = "zh_CN"

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

autoapi_dirs = ["../backend"]
autoapi_ignore = ["*_HOLIDAYS*"]


def setup(app):
    """Sphinx 构建前置钩子：从 FastAPI 应用生成 openapi.json。"""
    import json
    from backend.api.server import app
    output = os.path.join(os.path.dirname(__file__), "openapi.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)
    print(f"openapi.json 已生成: {output}")
