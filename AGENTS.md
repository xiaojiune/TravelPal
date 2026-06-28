# 绝对规则

- **语言**：推理内容（Thought）与对话内容必须使用中文。代码、变量名、API 字段保留英文，注释用中文。
- **搜索源**：Web 拉取时优先检索国内可达的中文源（如百度百科、知乎、CSDN 等）。

# 项目：TravelPal

基于双引擎 + LLM Agent 的智能旅游路径规划系统。
基于旧项目 D:\jb-file\python\TSPTW 的 visualization 分支改造。
需要参考旧代码时，使用 @old-project 引用。

## 代码规范

写代码时遵循 docs/coding_standards.md 中的接口清单规范与注释规范。

## 双终端协作

- **Alpha**：负责代码实现、架构变更、算法优化。执行具体的编码任务。
- **Bravo**：负责文档同步、架构记录、总结反思。维护 md 文件与规范。
- Alpha 完成代码变更后通过 relay 通知 Bravo 同步更新文档。