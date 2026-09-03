"""poi_cache 契约测试。

覆盖：缓存键幂等与命名空间、写入/读取往返、未命中返回 None、Redis 不可用降级。
不依赖真实 Redis：monkeypatch _get_redis 返回 fake client。
"""

import json

import backend.infrastructure.external.amap.poi_cache as pc  # noqa: E402


class FakeRedis:
    """内存 Redis 替身：dict 存值 + 记录 set 过期。"""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.expires: dict[str, int] = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value
        if ex is not None:
            self.expires[key] = ex


def _patch_redis(monkeypatch, fake: FakeRedis):
    monkeypatch.setattr(pc, "_get_redis", lambda: fake)


POI_ITEM = {
    "name": "岭南印象园",
    "lon": 113.34,
    "lat": 23.06,
    "address": "广州市番禺区",
    "tw_start": 540,
    "tw_end": 1140,
    "poi_type": "spot",
}


def test_poi_key_deterministic_and_scoped():
    key1 = pc.poi_key("广州", "岭南印象园")
    key2 = pc.poi_key("广州", "岭南印象园")
    assert key1 == key2
    assert key1.startswith("tp:poi:广州:")
    # 名称规范化：全角/空白归一化后指纹一致（同一 POI 跨写法命中同一键）
    key3 = pc.poi_key("广州", "  岭南印象园  ")
    assert key1 == key3
    # 城市不同 → 键不同
    key4 = pc.poi_key("深圳", "岭南印象园")
    assert key1 != key4


def test_poi_roundtrip(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    pc.set_poi_cached("广州", "岭南印象园", POI_ITEM)
    got = pc.get_poi_cached("广州", "岭南印象园")
    assert got == POI_ITEM
    assert fake.expires[pc.poi_key("广州", "岭南印象园")] == pc._POI_TTL


def test_poi_miss_returns_none(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    assert pc.get_poi_cached("广州", "广州塔") is None


def test_poi_redis_unavailable_degrades(monkeypatch):
    monkeypatch.setattr(pc, "_get_redis", lambda: None)
    assert pc.get_poi_cached("广州", "岭南印象园") is None
    pc.set_poi_cached("广州", "岭南印象园", POI_ITEM)  # 不抛异常


def test_poi_corrupt_value_returns_none(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    fake.store[pc.poi_key("广州", "岭南印象园")] = "not-json"  # 非法 JSON
    assert pc.get_poi_cached("广州", "岭南印象园") is None


def test_json_roundtrip_deserializes():
    raw = json.dumps(POI_ITEM, ensure_ascii=False)
    assert json.loads(raw) == POI_ITEM
