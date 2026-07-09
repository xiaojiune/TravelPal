#!/usr/bin/env python
"""高德 POI 搜索调试脚本：抓取指定名称的 POI 结果，展示原始返回数据。

用法：
    python tests/test_data/debug_poi.py "岭南印象园" 广州
"""

import sys
import requests
import os

AMAP_API_KEY = os.getenv("AMAP_API_KEY") or "d829ca668154dbc6800e83331819dfbf"


def search_poi(keywords: str, city: str, city_limit: bool = False):
    """直接调用高德 POI 搜索 API，返回完整 JSON。"""
    params = {
        "keywords": keywords,
        "city": city,
        "key": AMAP_API_KEY,
        "extensions": "all",
    }
    if city_limit:
        params["city_limit"] = "true"

    # 第一次：带 city_limit
    print(f"\n{'='*60}")
    print(f"请求：keywords={keywords!r}, city={city!r}, city_limit={city_limit}")
    print(f"URL：https://restapi.amap.com/v3/place/text")
    resp = requests.get("https://restapi.amap.com/v3/place/text", params=params, timeout=10)
    data = resp.json()
    print(f"status={data['status']}, count={data.get('count', 0)}, info={data.get('info', '')}")
    if data["status"] == "1" and int(data.get("count", 0)) > 0:
        for i, poi in enumerate(data["pois"]):
            loc = poi["location"]
            name = poi.get("name", "")
            pname = poi.get("pname", "")
            cityname = poi.get("cityname", "")
            adname = poi.get("adname", "")
            address = poi.get("address", "")
            biz_hours = ""
            if "biz_ext" in poi and "opentime2" in poi["biz_ext"]:
                biz_hours = poi["biz_ext"]["opentime2"]
            print(f"\n  [{i}] name={name!r}")
            print(f"       location={loc}")
            print(f"       province={pname}, city={cityname}, district={adname}")
            print(f"       address={address!r}")
            print(f"       opentime2={biz_hours!r}")
            print(f"       type={poi.get('type', '')}")
    else:
        print(f"  未找到结果")

    # 第二次：不带 city_limit（搜索全国）
    if city_limit:
        print(f"\n  --- 放宽到全国搜索（无 city_limit） ---")
        params2 = {k: v for k, v in params.items() if k != "city_limit"}
        resp2 = requests.get("https://restapi.amap.com/v3/place/text", params=params2, timeout=10)
        data2 = resp2.json()
        print(f"  status={data2['status']}, count={data2.get('count', 0)}, info={data2.get('info', '')}")
        if data2["status"] == "1" and int(data2.get("count", 0)) > 0:
            for i, poi in enumerate(data2["pois"][:5]):
                loc = poi["location"]
                name = poi.get("name", "")
                pname = poi.get("pname", "")
                cityname = poi.get("cityname", "")
                adname = poi.get("adname", "")
                address = poi.get("address", "")
                print(f"\n    [{i}] name={name!r}")
                print(f"         location={loc}")
                print(f"         province={pname}, city={cityname}, district={adname}")
                print(f"         address={address!r}")
                print(f"         type={poi.get('type', '')}")

    return data


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    keywords = args[0]
    city = args[1]
    search_poi(keywords, city, city_limit=True)
