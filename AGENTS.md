# 绝对规则

- **语言**：推理内容（Thought）与对话内容必须使用中文。代码、变量名、API 字段保留英文，注释用中文。
- **搜索源**：Web 拉取时优先检索国内可达的中文源（如百度百科、知乎、CSDN 等）。

# 项目：TravelPal

基于双引擎 + LLM Agent 的智能旅游路径规划系统。
基于旧项目 D:\jb-file\python\TSPTW 的 visualization 分支改造。
需要参考旧代码时，使用 @old-project 引用。

## 代码规范

写代码时参考 docs/coding_standards.md 中的注释与编码规范。

### 接口变更工作流

修改函数签名或新增公开 API 时，遵循以下顺序：
1. 先更新 `src/engine/__init__.py`（或 `src/data/__init__.py`）顶部的接口清单注释块
2. 再修改对应的实现文件
3. 确保接口清单与 `__all__` 列表保持同步