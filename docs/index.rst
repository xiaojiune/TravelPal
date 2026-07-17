欢迎使用 TravelPal
====================

旅行伴侣 —— 基于双引擎 + LLM Agent 的智能旅行规划系统。

.. toctree::
   :maxdepth: 2
   :caption: 架构与设计

   ADR/001
   ADR/002
   ADR/003
   ADR/004
   ADR/005

.. toctree::
   :maxdepth: 1
   :caption: 规范与路线图

   coding
   产品路线图

.. toctree::
   :maxdepth: 2
   :caption: 项目结构与部署

   structure/project
   structure/backend
   structure/data
   structure/frontend
   dev-env

.. toctree::
   :maxdepth: 2
   :caption: Python API 参考

   autoapi/index

REST API
--------

启动后端后访问 ``http://localhost:8000/docs`` (Swagger UI 交互式文档)。

原始 OpenAPI 规范 (供 Orval 等工具使用)：``http://localhost:8000/openapi.json``。
