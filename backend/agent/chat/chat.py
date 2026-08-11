"""对话消息构建：注入 README 项目自述与规划概要。

编排（LLM 调用 + 工具分发 + SSE 事件流）已由 orchestrator.py（LangGraph）接管，
本模块仅保留消息组装职责。

RAG 文档检索注入已移除（2026-08-08，用户决定暂缓重构，待后续再议）。
"""

import json
import os

from backend.agent.prompts import CHAT_SYSTEM

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _readme_core() -> str:
    """读取 README.md 标题 + 核心功能 + 技术栈，作为项目介绍兜底。"""
    path = os.path.join(_PROJECT_ROOT, "README.md")
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        # 取标题 + 核心功能 + 技术栈（约前 130 行）
        core = "".join(lines[:130])
        return f"\n\n## 项目自述（来自 README.md）\n{core[:2000]}"
    except Exception:
        return ""


def build_chat_messages(
    message: str,
    plan_result: dict | None = None,
    form_context: dict | None = None,
) -> list[dict]:
    """构建对话消息列表。

    Args:
        message: 用户输入的消息。
        plan_result: 可选的规划结果，注入 system prompt 作为上下文。
        form_context: 可选的表单输入快照（城市/酒店/景点名列表），
            非空时注入 system prompt，供 Agent 感知用户已填内容。

    Returns:
        OpenAI-compatible messages 列表。
    """
    system = CHAT_SYSTEM
    if plan_result:
        summary = {
            "city": plan_result.get("city", "未知"),
            "n_days": plan_result.get("best_days", 0),
            "total_cost": plan_result.get("solution", {}).get("total_cost", 0),
            "commentary": plan_result.get("commentary", ""),
        }
        system += f"\n\n当前规划概要（供参考）：\n{json.dumps(summary, ensure_ascii=False)}"

    if form_context:
        fc = {
            "city": form_context.get("city", ""),
            "hotel_name": form_context.get("hotel_name", ""),
            "spot_names": [s.get("name") for s in form_context.get("spots", [])],
            "n_days": form_context.get("n_days"),
        }
        system += f"\n\n用户已填写的表单（当前状态，供参考）：\n{json.dumps(fc, ensure_ascii=False)}"

    system += _readme_core()

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]
