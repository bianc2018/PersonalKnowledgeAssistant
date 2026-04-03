# TODOS

本文件记录项目待办事项，按优先级排序。

## 高优先级（MVP 必需）

### TODO-001: 实现异步任务队列（Celery/RQ）
- **What:** 为技术调研任务实现异步处理，避免 API 长时间等待
- **Why:** 调研涉及搜索+LLM多次调用，可能耗时30-60秒，同步请求会超时
- **Context:** 使用 Celery + Redis 或 RQ，调研请求立即返回 task_id，客户端轮询状态
- **Depends on:** 无
- **Created:** 2025-04-03

### TODO-002: 实现 SearXNG Docker 配置
- **What:** 配置 SearXNG 元搜索引擎作为 Docker Compose 服务
- **Why:** 搜索是技术调研的核心依赖，SearXNG 无需 API Key 且隐私友好
- **Context:** 参考 SearXNG 官方 Docker 镜像，配置多引擎聚合（Google/Bing/DuckDuckGo）
- **Depends on:** 无
- **Created:** 2025-04-03

## 中优先级（V2 功能）

### TODO-003: 添加本地 Ollama 支持
- **What:** 实现本地 LLM 调用，用于简单任务和隐私脱敏
- **Why:** 降低 API 成本，保护敏感数据
- **Context:** 设计 LLM 路由层，根据任务类型自动选择商业模型或本地模型
- **Depends on:** MVP 架构验证完成
- **Created:** 2025-04-03

### TODO-004: 实现知识图谱可视化
- **What:** 场景4（文档上传）的图谱展示功能
- **Why:** 让用户直观看到知识关联
- **Context:** 使用 D3.js 或 Cytoscape.js 展示实体-关系图
- **Depends on:** 场景2 MVP 完成
- **Created:** 2025-04-03

### TODO-005: 实现领域定时跟踪
- **What:** 场景5的定时任务（每日/每周扫描）
- **Why:** 持续跟踪技术领域最新进展
- **Context:** 使用 APScheduler 或 Celery Beat 实现定时任务
- **Depends on:** 异步任务队列（TODO-001）完成
- **Created:** 2025-04-03

## 低优先级（增强功能）

### TODO-006: 评估 PostgreSQL + pgvector 迁移
- **What:** 评估将 SQLite+Chroma 迁移到 PostgreSQL+pgvector
- **Why:** 统一数据源，支持事务和复杂查询
- **Context:** 仅在数据量增长后评估，MVP 保持轻量
- **Depends on:** 数据量 > 10GB 或需要复杂查询
- **Created:** 2025-04-03

### TODO-007: 添加 Web UI
- **What:** 使用 Streamlit 或 Gradio 构建 Web 界面
- **Why:** 比 CLI 更友好的用户体验
- **Context:** 调研报告展示、知识图谱可视化、对话界面
- **Depends on:** API 稳定后
- **Created:** 2025-04-03
