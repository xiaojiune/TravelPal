欢迎使用 TravelPal
====================

旅行伴侣 —— 基于双引擎 + LLM Agent 的智能旅行规划系统。

.. note::

   文档状态说明：

   - 各包的**代码规范**已确立（见 ``travelpal-coding`` skill）
   - ADR / product / runbooks 包**可供阅读**，但信息不一定准确
   - structure / 包**内容过时**，暂不可作为依据
   - 阅读时请以各文档「修改记录」的**日期**为准

.. toctree::
   :maxdepth: 2
   :caption: 架构与设计（ADR）

   ADR/001
   ADR/002
   ADR/003
   ADR/004
   ADR/005
   ADR/006
   ADR/007
   ADR/008
   ADR/009
   ADR/010
   ADR/011
   ADR/012
   ADR/013
   ADR/014
   ADR/015

.. list-table:: ADR 索引
   :header-rows: 1

   * - 编号
     - 标题
     - 生命周期
   * - ADR-001
     - CA / VNS 平级并行架构
     - Accepted
   * - ADR-002
     - 前端架构选型
     - Accepted
   * - ADR-003
     - 可视化方案变更——Cesium 3D → AMap 2D
     - Accepted
   * - ADR-004
     - 项目哲学——"旅行伴侣"而非"规划工具"
     - Accepted
   * - ADR-005
     - 营业时间 LLM 解析与 Agent 架构决策
     - Accepted
   * - ADR-006
     - MCP 协议迁移预留
     - Accepted
   * - ADR-007
     - BM25 RAG 知识检索
     - Accepted
   * - ADR-008
     - 架构演进路线图
     - Accepted
   * - ADR-009
     - 前端组件库引入策略——Naive UI 分步替换
     - Accepted
   * - ADR-010
     - 后端架构评估与技术债清单
     - Accepted
   * - ADR-011
     - 前端架构评估与技术债清单
     - Accepted
   * - ADR-012
     - 采用手写轻量级架构替代 LangChain 全栈框架
     - Accepted
   * - ADR-013
     - 前端 UI/UX 设计模式与方案取舍
     - Accepted
   * - ADR-014
     - LLM 编排层选型——LangGraph 维持，PydanticAI 不引入
     - Accepted
   * - ADR-015
     - 用户记忆与 balance——遗留函数的重新审视
     - Accepted

.. toctree::
   :maxdepth: 2
   :caption: 项目结构

   structure/project
   structure/backend
   structure/frontend
   structure/agent
   structure/data
   structure/tools

.. toctree::
   :maxdepth: 1
   :caption: 规范与路线图

   product/slogan
   product/产品路线图

.. toctree::
   :maxdepth: 2
   :caption: Python API 参考

   autoapi/index

REST API
--------

启动后端后访问 ``http://localhost:8000/docs`` (Swagger UI 交互式文档)。

原始 OpenAPI 规范 (供 Orval 等工具使用)：``http://localhost:8000/openapi.json``。
