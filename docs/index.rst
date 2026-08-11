欢迎使用 TravelPal
====================

旅行伴侣 —— 基于双引擎 + LLM Agent 的智能旅行规划系统。

.. note::

   文档状态说明：

   - 各包的**代码规范**已确立（见 ``runbooks/coding``）
   - ADR / product / runbooks 包**可供阅读**，但信息不一定准确
   - structure / 包**内容过时**，暂不可作为依据
   - 阅读时请以各文档「修改记录」的**日期**为准

.. toctree::
   :maxdepth: 2
   :caption: 架构与设计

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
   ADR/README

.. toctree::
   :maxdepth: 2
   :caption: 项目结构

   structure/project
   structure/backend
   structure/frontend
   structure/agent
   structure/data
   structure/tools
   structure/README

.. toctree::
   :maxdepth: 1
   :caption: 规范与路线图

   runbooks/coding
   runbooks/git
   product/README
   product/slogan
   product/产品路线图
   runbooks/deploy
   runbooks/troubleshooting
   runbooks/README

.. toctree::
   :maxdepth: 2
   :caption: Python API 参考

   autoapi/index

REST API
--------

启动后端后访问 ``http://localhost:8000/docs`` (Swagger UI 交互式文档)。

原始 OpenAPI 规范 (供 Orval 等工具使用)：``http://localhost:8000/openapi.json``。
