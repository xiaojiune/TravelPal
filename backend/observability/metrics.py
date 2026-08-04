"""Prometheus 观测性指标定义与多进程聚合。

设计说明：
- 所有指标统一注册到自定义 REGISTRY，避免与第三方库的默认注册表冲突。
- 多进程模式：backend（FastAPI）与 celery worker 是独立进程，通过共享
  PROMETHEUS_MULTIPROC_DIR 目录（mmap 文件）采集各自进程内指标，
  /api/metrics 端点用 MultiProcessCollector 聚合全部进程的指标。
- 接入 Prometheus 时（当前仅端点就绪，未部署）：
  scrape_configs 增加一个 job，指向 http://<host>/api/metrics，
  若启用了 Nginx Basic Auth 则配置 basic_auth（用户名/密码与 .htpasswd 一致）。
- TODO：部署 Prometheus/Grafana 时在此补充 scrape_configs 示例与告警规则。
"""

import os

from backend.config import PROMETHEUS_MULTIPROC_DIR

# 必须在 import prometheus_client 之前设置环境变量：
# prometheus_client 在模块导入时通过 get_value_class() 一次性决定单/多进程模式
# （values.py 模块级 `ValueClass = get_value_class()`），之后修改 os.environ 不会生效。
# 若顺序颠倒，所有 Metric 将锁定单进程内存模式，worker 侧指标无法写入共享 mmap。
if PROMETHEUS_MULTIPROC_DIR:
    os.makedirs(PROMETHEUS_MULTIPROC_DIR, exist_ok=True)
    os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", PROMETHEUS_MULTIPROC_DIR)

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)

REGISTRY = CollectorRegistry()


# ================== LLM ==================
# kind: complete（非流式）/ stream（流式）/ parse_biz_hours（营业时间解析）
llm_calls = Counter(
    "travelpal_llm_calls_total",
    "LLM 调用次数，按调用类型区分",
    ["kind"],
    registry=REGISTRY,
)
# direction: prompt / completion（DeepSeek 两者单价不同，分开计量）
llm_tokens = Counter(
    "travelpal_llm_tokens_total",
    "LLM token 消耗，按调用类型与输入/输出方向区分",
    ["kind", "direction"],
    registry=REGISTRY,
)

# ================== 驾车 API ==================
# result: success / fail（单次路径规划）
driving_calls = Counter(
    "travelpal_driving_calls_total",
    "驾车路径 API 调用次数，按结果区分",
    ["result"],
    registry=REGISTRY,
)
# 驾车 API 单次耗时（秒级直方图，覆盖数秒~数十秒）
driving_duration = Histogram(
    "travelpal_driving_duration_seconds",
    "驾车路径 API 单次调用耗时（秒）",
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300),
    registry=REGISTRY,
)
# 成本矩阵构建总耗时（含对称复用，验证 40s 大头在 API 拉取）
matrix_build_duration = Histogram(
    "travelpal_matrix_build_duration_seconds",
    "驾车成本矩阵构建总耗时（秒）",
    buckets=(10, 30, 60, 120, 300, 600),
    registry=REGISTRY,
)

# ================== 异步任务（celery worker 侧） ==================
# task_type: suggest / plan；status: success / failed
task_total = Counter(
    "travelpal_task_total",
    "异步规划任务完成数，按类型与结果区分",
    ["task_type", "status"],
    registry=REGISTRY,
)
task_duration = Histogram(
    "travelpal_task_duration_seconds",
    "异步规划任务执行耗时（秒）",
    ["task_type"],
    buckets=(5, 15, 30, 60, 120, 300, 600, 900),
    registry=REGISTRY,
)

# ================== HTTP（FastAPI 侧） ==================
http_requests = Counter(
    "travelpal_http_requests_total",
    "HTTP 请求数，按方法/路径/状态码区分",
    ["method", "path", "status"],
    registry=REGISTRY,
)
http_duration = Histogram(
    "travelpal_http_duration_seconds",
    "HTTP 请求耗时（秒）",
    ["method", "path"],
    registry=REGISTRY,
)


def metrics_response() -> tuple[str, bytes]:
    """生成 /api/metrics 端点响应体。

    Returns:
        (content_type, body): Prometheus 文本格式的指标序列化结果。

    设计说明：
    - 多进程模式：使用独立 exposition registry + MultiProcessCollector，
      从共享目录 mmap 文件重建全部进程（backend + worker）的指标，
      避免 REGISTRY 中 counter 对象自身 collect 与聚合结果重复计数。
    - 单进程模式（未配置目录）：直接输出 REGISTRY 中定义的指标。
    """
    if PROMETHEUS_MULTIPROC_DIR:
        exposition_registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(exposition_registry)
        return CONTENT_TYPE_LATEST, generate_latest(exposition_registry)
    return CONTENT_TYPE_LATEST, generate_latest(REGISTRY)
