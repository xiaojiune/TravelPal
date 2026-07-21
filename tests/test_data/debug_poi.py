#!/usr/bin/env python
"""高德 POI 搜索调试脚本，展示原始返回数据。

用法（在 Windows .venv 下运行）：
    python tests/test_data/debug_poi.py "岭南印象园" 广州
"""

import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dotenv import load_dotenv

load_dotenv()
AMAP_API_KEY = os.getenv("AMAP_API_KEY")


def search_poi(keywords: str, city: str):
    """调用高德 POI 搜索 API，展示各策略结果。"""
    base = {"keywords": keywords, "city": city, "key": AMAP_API_KEY, "extensions": "all"}

    configs = [
        ("策略1: types+city_limit", {**base, "city_limit": True, "types": "风景名胜"}),
        ("策略2: 无types+city_limit", {**base, "city_limit": True}),
        ("策略3: 全国搜索(无city_limit)", {k: v for k, v in base.items()}),
    ]

    for label, params in configs:
        print(f"\n{'=' * 60}")
        print(f"{label}")
        print(f"keywords={keywords!r}, city={city!r}")
        resp = requests.get("https://restapi.amap.com/v3/place/text", params=params, timeout=10)
        data = resp.json()
        count = int(data.get("count", 0))
        print(f"status={data['status']}, count={count}, info={data.get('info', '')}")

        if data["status"] == "1" and count > 0:
            for i, poi in enumerate(data["pois"][:5]):
                name = poi.get("name", "")
                loc = poi["location"]
                pname = poi.get("pname", "")
                cityname = poi.get("cityname", "")
                address = poi.get("address", "")
                biz_hours = poi.get("biz_ext", {}).get("opentime2", "") if "biz_ext" in poi else ""
                print(f"\n  [{i}] name={name!r}")
                print(f"       location={loc}")
                print(f"       city={pname}{cityname}")
                print(f"       address={address!r}")
                if biz_hours:
                    print(f"       opentime2={biz_hours!r}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    search_poi(args[0], args[1])
