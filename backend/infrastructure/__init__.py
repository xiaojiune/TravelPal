"""基础设施层：可插拔的领域实现（LLM 接入、检索等）。

实现类必须满足 backend/domain/ 中定义的 Protocol，
由各 factory 负责实例化与切换，领域层与编排层不感知具体框架。
"""
