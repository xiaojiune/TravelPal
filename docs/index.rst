欢迎使用 TravelPal
====================

.. note::

   文档状态说明：

   - 阅读时请以各文档「修改记录」中的**最新日期**为准，判断内容是否适用于当前代码版本。
   - 文档遵循「独立生命体」原则：**落后 ≠ 失效**，每篇是其所覆盖时间段的当时事实；标注「过时 / Deprecated」的文档仅作参考，不再代表当前实现。
   - 各目录定位速览：``ADR/`` 决策依据、``design/`` 规划蓝图、``product/`` 做成什么、``structure/`` 当前架构快照。

.. toctree::
   :hidden:
   :maxdepth: 1
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

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: 规划蓝图（design）

   design/architecture
   design/ui-ux
   design/memory
   design/user-system

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: 规范与路线图（product）

   product/slogan
   product/philosophy
   product/roadmap

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: 项目结构

   structure/project
   structure/backend
   structure/frontend
   structure/agent
   structure/data
   structure/tools

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: 会话交接（handoff）

   handoff/CURRENT_CODE
   handoff/CURRENT_DOC

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Python API 参考

   autoapi/index

文件导航
--------

.. list-table::
   :header-rows: 1

   * - 目录
     - 职责
     - 入口
   * - ``ADR/``
     - 决策记录（选了什么、为什么、代价），共 11 篇
     - :doc:`ADR/001` ～ :doc:`ADR/011`
   * - ``design/``
     - 规划蓝图（往哪走：演进路线 / UI-UX / 记忆 / 用户系统），共 4 篇
     - :doc:`design/architecture`、:doc:`design/ui-ux`、:doc:`design/memory`、:doc:`design/user-system`
   * - ``product/``
     - 产品与哲学（使命→原则→计划），共 3 篇
     - :doc:`product/slogan`、:doc:`product/philosophy`、:doc:`product/roadmap`
   * - ``structure/``
     - 结构详解（各层当前架构快照），共 6 篇
     - :doc:`structure/project`、:doc:`structure/backend`、:doc:`structure/frontend`、:doc:`structure/agent`、:doc:`structure/data`、:doc:`structure/tools`
   * - ``handoff/``
     - 会话交接（本会话做到哪、下一步做什么），CURRENT_CODE / CURRENT_DOC
     - :doc:`handoff/CURRENT_CODE`、:doc:`handoff/CURRENT_DOC`

REST API
--------

启动后端后访问 ``http://localhost:8000/docs`` (Swagger UI 交互式文档)。

原始 OpenAPI 规范 (供 Orval 等工具使用)：``http://localhost:8000/openapi.json``。

.. comment::
   ADR 索引表（编号/标题/生命周期）原在主页正文。为保持主页精简，已收敛到侧边栏 toctree 单一来源，不再于正文渲染。

   .. list-table::
      :hidden:
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
        - 营业时间 LLM 解析与 Agent 架构决策
        - Accepted
      * - ADR-005
        - MCP 协议迁移预留
        - Accepted
      * - ADR-006
        - BM25 RAG 知识检索
        - Deprecated
      * - ADR-007
        - 前端组件库引入策略——Naive UI 分步替换
        - Accepted
      * - ADR-008
        - 手写轻量架构 + 选择性引框架（LangChain 生态边界）
        - Accepted
      * - ADR-009
        - LLM 编排层选型——LangGraph 维持，PydanticAI 不引入
        - Accepted