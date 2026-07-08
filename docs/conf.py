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
