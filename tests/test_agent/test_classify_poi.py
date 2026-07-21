"""POI 类型判定 _classify_poi() 单元测试。"""

from backend.agent.tools.poi import _classify_poi


class TestClassifyPoi:
    def test_hotel_by_type(self):
        assert _classify_poi("住宿服务;宾馆酒店", "悦朵酒店") == "hotel"

    def test_hotel_by_name(self):
        assert _classify_poi("餐饮服务;中餐厅", "广州白天鹅宾馆") == "hotel"

    def test_spot_museum(self):
        assert _classify_poi("风景名胜;博物馆", "故宫博物院") == "spot"

    def test_spot_park(self):
        assert _classify_poi("风景名胜;公园", "白云山") == "spot"

    def test_unknown_category(self):
        assert _classify_poi("餐饮服务;中餐厅", "陶陶居") == "spot"
