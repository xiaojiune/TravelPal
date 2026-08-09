"""driving_cache 矩阵快照契约测试。

覆盖：矩阵键指纹构造、快照写入/读取往返、命中滑动续期、Redis 不可用降级。
不依赖真实 Redis：monkeypatch _get_redis 返回 fake client。
"""

import json

import backend.data.driving_cache as dc  # noqa: E402


class FakeRedis:
    """内存 Redis 替身：dict 存值 + 记录 expire 调用。"""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.expires: dict[str, int] = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value
        if ex is not None:
            self.expires[key] = ex

    def expire(self, key, ttl):
        self.expires[key] = ttl


POI_NAMES = ["酒店", "广州塔", "白云山"]
COORDS = [(113.3, 23.1), (113.32, 23.1), (113.28, 23.18)]
SNAPSHOT = {
    "cost": [[0.0, 10.0, 15.0], [10.0, 0.0, 12.0], [15.0, 12.0, 0.0]],
    "dist": [[0.0, 5.0, 8.0], [5.0, 0.0, 6.0], [8.0, 6.0, 0.0]],
    "polylines": {"0_1": "113.3,23.1;113.32,23.1", "1_0": "113.32,23.1;113.3,23.1"},
}


def _patch_redis(monkeypatch, fake: FakeRedis):
    monkeypatch.setattr(dc, "_get_redis", lambda: fake)


def test_matrix_key_deterministic_and_order_sensitive():
    key1 = dc.matrix_key("广州", POI_NAMES, COORDS)
    key2 = dc.matrix_key("广州", POI_NAMES, COORDS)
    assert key1 == key2
    assert key1.startswith("tp:matrix:广州:")
    # 点顺序不同 → 键不同（顺序指纹）
    key3 = dc.matrix_key("广州", POI_NAMES[::-1], COORDS[::-1])
    assert key1 != key3
    # 城市不同 → 键不同
    key4 = dc.matrix_key("北京", POI_NAMES, COORDS)
    assert key1 != key4


def test_matrix_roundtrip(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    dc.set_driving_matrix("广州", POI_NAMES, COORDS, SNAPSHOT)
    got = dc.get_driving_matrix("广州", POI_NAMES, COORDS)
    assert got == SNAPSHOT
    assert fake.expires[dc.matrix_key("广州", POI_NAMES, COORDS)] == dc._MATRIX_TTL


def test_matrix_hit_sliding_renewal(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    dc.set_driving_matrix("广州", POI_NAMES, COORDS, SNAPSHOT)
    key = dc.matrix_key("广州", POI_NAMES, COORDS)
    fake.expires[key] = 100  # 模拟 TTL 已衰减
    dc.get_driving_matrix("广州", POI_NAMES, COORDS)
    assert fake.expires[key] == dc._MATRIX_TTL  # 命中后续期回满


def test_matrix_miss_returns_none(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    assert dc.get_driving_matrix("广州", POI_NAMES, COORDS) is None


def test_matrix_redis_unavailable_degrades(monkeypatch):
    monkeypatch.setattr(dc, "_get_redis", lambda: None)
    assert dc.get_driving_matrix("广州", POI_NAMES, COORDS) is None
    dc.set_driving_matrix("广州", POI_NAMES, COORDS, SNAPSHOT)  # 不抛异常


def test_pair_cache_unaffected(monkeypatch):
    fake = FakeRedis()
    _patch_redis(monkeypatch, fake)
    origin = {"name": "酒店", "lon": 113.3, "lat": 23.1}
    dest = {"name": "广州塔", "lon": 113.32, "lat": 23.1}
    dc.set_driving_pair("广州", origin, dest, {"duration_min": 10.0, "distance_km": 5.0})
    got = dc.get_driving_pair("广州", origin, dest)
    assert got == {"duration_min": 10.0, "distance_km": 5.0}
    # 点对键与矩阵键命名空间独立
    assert not fake.store[dc.pair_key("广州", origin, dest)].startswith("tp:matrix:")


def test_json_roundtrip_deserializes():
    raw = json.dumps(SNAPSHOT, ensure_ascii=False)
    assert json.loads(raw) == SNAPSHOT
