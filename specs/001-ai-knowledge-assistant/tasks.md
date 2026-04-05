# Tasks: AI 知识管理助手

**Input**: Design documents from `/specs/001-ai-knowledge-assistant/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 项目初始化与基础目录结构

- [ ] T001 创建项目目录结构：按 plan.md 建立 `src/` 下 `auth/`、`knowledge/`、`chat/`、`research/`、`profile/`、`db/`、`search/`、`external/`、`tasks/` 及 `tests/`
- [ ] T002 创建 `requirements.txt` 并安装依赖：FastAPI、uvicorn、sqlite-vec、aiosqlite、httpx、pydantic-settings、cryptography、argon2-cffi、pytest、pytest-asyncio
- [ ] T003 [P] 配置 pytest 异步测试环境：创建 `tests/conftest.py` 并配置内存数据库 fixture

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 核心基础设施，必须在任何用户故事之前完成

**⚠️ CRITICAL**: 基础层未完成前，禁止开始任何用户故事实现

- [ ] T004 创建完整数据库 Schema：在 `src/db/schema.sql` 中定义所有实体表（KnowledgeItem、KnowledgeVersion、Attachment、Tag、TagLink、EmbeddingChunk、ConfidenceEvaluation、Conversation、Message、MessageCitation、UserProfile、ResearchTask、ResearchSection、ResearchCitation、SystemConfig）及 sqlite-vec / FTS5 虚拟表
- [ ] T005 [P] 实现 aiosqlite 连接管理：在 `src/db/connection.py` 中封装连接获取、加载 sqlite-vec 扩展、Schema 自动初始化
- [ ] T006 [P] 实现配置模型：在 `src/config.py` 中使用 Pydantic Settings 定义 LLM、Embedding、搜索、隐私策略、重试、存储、日志配置
- [ ] T007 [P] 实现加密与密钥派生：在 `src/auth/crypto.py` 中实现 Argon2id 密码派生和 AES-256-GCM 文件加解密
- [ ] T008 [P] 实现 JWT 鉴权依赖：在 `src/auth/dependencies.py` 中实现 `get_current_user` 依赖与 Token 校验
- [ ] T009 实现认证路由：在 `src/auth/router.py` 中实现 `POST /api/auth/login`（含 24h / 7 天 Token 切换）
- [ ] T010 [P] 实现外部请求重试模块：在 `src/external/retry.py` 中实现指数退避（最多 3 次、1s→2s→4s）与超时配置
- [ ] T011 [P] 实现 LLM API 客户端：在 `src/external/llm.py` 中封装兼容 OpenAI API 的聊天与 Embedding 调用，支持流式响应

**Checkpoint**: 应用可启动，数据库可连接，鉴权链路可跑通

---

## Phase 3: User Story 1 - 添加并管理个人知识 (Priority: P1) 🎯 MVP

**Goal**: 用户能够添加、浏览、搜索、删除（软删除）知识条目；支持标签和多格式附件。

**Independent Test**: 通过 API 上传一条文本知识并保存，随后在列表中搜索关键词能命中该知识，验证标题和内容正确展示。

### Implementation for User Story 1

- [ ] T012 [P] [US1] 创建 knowledge Pydantic 模型：在 `src/knowledge/models.py` 中定义请求/响应模型（知识创建、更新、列表、详情、标签）
- [ ] T013 [P] [US1] 实现多媒体文本提取器：在 `src/knowledge/extractor.py` 中实现文本、PDF、DOCX、HTML 提取，图片 OCR 与音视频转录按最佳 effort 处理并标记失败状态
- [ ] T014 [US1] 实现知识业务服务层：在 `src/knowledge/service.py` 中实现标签 CRUD、知识条目 CRUD（含版本生成）、软删除、附件加密存储、列表搜索（按关键词/标签）
- [ ] T015 [US1] 实现知识库路由：在 `src/knowledge/router.py` 中实现 `POST /api/knowledge`、`POST /api/knowledge/upload`、`POST /api/knowledge/url`、`GET /api/knowledge`（搜索列表）、`GET /api/knowledge/{id}`、`PATCH /api/knowledge/{id}`、`DELETE /api/knowledge/{id}`、`GET /api/knowledge/tags`

**Checkpoint**: US1 独立可用，用户可完成“添加→搜索→查看→删除”闭环

---

## Phase 4: User Story 2 - 对话式查询知识 (Priority: P1)

**Goal**: 用户通过自然语言对话查询个人知识库，系统基于 RAG 返回带引用的回答；支持会话列表和历史继续。

**Independent Test**: 知识库中已保存一条关于某主题的知识后，用自然语言提问该主题，系统回答必须引用该知识内容；无相关内容时拒绝编造。

### Implementation for User Story 2

- [ ] T016 [P] [US2] 创建 chat Pydantic 模型：在 `src/chat/models.py` 中定义会话、消息、引用、流式增量响应模型
- [ ] T017 [P] [US2] 实现 sqlite-vec 向量操作：在 `src/search/vec.py` 中实现 embedding 插入、Top-K 相似度搜索
- [ ] T018 [P] [US2] 实现 FTS5 全文检索：在 `src/search/fts.py` 中实现文本分片插入、关键词搜索（bm25 排序）
- [ ] T019 [P] [US2] 实现混合检索排序：在 `src/search/hybrid.py` 中并行召回向量/FTS5 各 Top-15，去重合并后按加权分数取 Top-10
- [ ] T020 [US2] 实现对话与 RAG 服务层：在 `src/chat/service.py` 中实现会话/消息 CRUD、RAG 上下文组装、LLM 回答生成（含引用解析）、无结果时拒绝回答
- [ ] T021 [US2] 实现对话路由：在 `src/chat/router.py` 中实现 `GET /api/chat/conversations`、`POST /api/chat/conversations`、`GET /api/chat/conversations/{id}/messages`、`POST /api/chat/conversations/{id}/messages`（含 SSE 流式响应）

**Checkpoint**: US2 独立可用，RAG 查询能正确引用知识库内容

---

## Phase 5: User Story 3 - 生成领域调研报告 (Priority: P2)

**Goal**: 用户提交调研主题，系统异步检索网络信息并生成结构化报告；页面通过 SSE 实时展示进度，遇到分支决策时暂停并向用户提问。

**Independent Test**: 提交“低空经济政策分析”主题，订阅 SSE 查看进度更新；若系统提出决策问题，用户选择后调研继续，最终生成包含 background / key_points / trends / conclusion 的报告。

### Implementation for User Story 3

- [ ] T022 [P] [US3] 创建 research Pydantic 模型：在 `src/research/models.py` 中定义任务、章节、引用、决策响应模型
- [ ] T023 [P] [US3] 实现搜索源适配层：在 `src/external/search.py` 中实现 LLM 自带搜索、独立搜索 API（Tavily/SerpAPI）、HTTP 爬虫三种适配器及优先级回退
- [ ] T024 [P] [US3] 实现异步任务队列：在 `src/tasks/queue.py` 中实现基于 `asyncio.Queue` 的并发控制、任务状态持久化、`pending_recheck` 自动恢复机制
- [ ] T025 [P] [US3] 实现调研业务服务层：在 `src/research/service.py` 中实现调研任务 CRUD、进度更新、章节/引用存储、保存到知识库
- [ ] T026 [US3] 实现调研工作协程：在 `src/research/worker.py` 中实现大纲生成→网络检索→章节撰写→汇总报告流程，支持暂停提问与恢复继续
- [ ] T027 [US3] 实现调研路由：在 `src/research/router.py` 中实现 `POST /api/research`、`GET /api/research`、`GET /api/research/{id}`、`GET /api/research/{id}/events`（SSE）、`POST /api/research/{id}/respond`、`POST /api/research/{id}/save`

**Checkpoint**: US3 独立可用，异步调研全链路跑通，SSE 进度正常，人机决策可恢复

---

## Phase 6: User Story 4 - 知识置信度评估 (Priority: P2)

**Goal**: 系统对每个知识版本自动进行置信度评分并可视化展示评分与依据；支持手动触发重新评估，旧版本评估记录独立保留。

**Independent Test**: 上传一条知识并保存，系统自动完成评估，详情页显示评分依据；修改内容后触发新版本并自动重新评估，旧版本评估记录不变。

### Implementation for User Story 4

- [ ] T028 [P] [US4] 实现置信度评估服务：在 `src/knowledge/confidence.py` 中实现调用 LLM 进行验证，输出 `score_level`（high/medium/low）、`method`、`rationale`
- [ ] T029 [US4] 集成自动评估触发：在 `src/knowledge/service.py` 的知识入库/更新逻辑中，当 `content_delta > 0.2` 时自动调用置信度评估
- [ ] T030 [US4] 添加手动触发端点：在 `src/knowledge/router.py` 中实现 `POST /api/knowledge/{id}/evaluate-confidence`

**Checkpoint**: US4 独立可用，自动与手动评估均正常工作，历史版本评估隔离

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 系统级功能完善与跨用户故事增强

- [ ] T031 [P] 创建 profile Pydantic 模型：在 `src/profile/models.py` 中定义 UserProfile 模型
- [ ] T032 [P] 实现用户画像服务：在 `src/profile/service.py` 中实现基于对话历史提取领域偏好与知识水平，每 5 轮或新领域触发更新
- [ ] T033 [P] 实现系统路由：在 `src/system/router.py` 中实现 `POST /api/system/init`、`GET /api/system/status`、`GET/PUT /api/system/config`、`POST /api/system/export`、`POST /api/system/import`、`POST /api/system/reset`
- [ ] T034 [P] 实现系统级业务逻辑：在 `src/system/service.py` 中实现配置读写、ZIP 导出/导入（含 metadata.json、跳过损坏文件、重算向量）、版本保留策略与日志清理
- [ ] T035 [P] 实现降级与容错逻辑：在 `src/external/llm.py` 和 `src/external/search.py` 中检测外部服务不可用，自动切换本地模型并提示“降级模式”；维护 `pending_recheck` 与恢复重跑
- [ ] T036 [P] 实现旧媒体归档压缩：在 `src/knowledge/service.py`（或新建 `src/knowledge/archive.py`）中实现超过磁盘阈值时对旧附件自动 gzip 归档
- [ ] T037 配置日志与全局错误处理：在 `src/main.py` 中配置应用日志、静态文件挂载、全局异常处理器
- [ ] T038 [P] 运行端到端验证：按 `quickstart.md` 完成安装→启动→添加知识→对话→调研→导出流程，验证 SC-001 ~ SC-005

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → 无依赖，可立即开始
- **Foundational (Phase 2)** → 依赖 Setup 完成 → **阻塞所有用户故事**
- **User Stories (Phase 3-6)** → 均依赖 Foundational 完成
- **Polish (Phase 7)** → 依赖 US1 ~ US4 核心功能稳定后实施

### User Story Dependencies

| Story | 前置依赖 | 说明 |
|-------|----------|------|
| US1 (P1) | Phase 2 Foundational | 无其他故事依赖，MVP 首选项 |
| US2 (P1) | Phase 2 + US1 | RAG 需要知识库数据和嵌入向量写入能力 |
| US3 (P2) | Phase 2 + US1 | 调研报告保存到知识库依赖 US1 的入库能力 |
| US4 (P2) | Phase 2 + US1 | 置信度评估依赖知识版本模型 |

### Parallel Opportunities

- **Phase 1**: T003 与 T001/T002 可并行
- **Phase 2**: T005 ~ T008、T010、T011 可并行（不同文件，无相互依赖）
- **Phase 3 (US1)**: T012 与 T013 可并行；T014 依赖 T012/T013；T015 依赖 T014
- **Phase 4 (US2)**: T016 ~ T019 可并行；T020 依赖 T016 ~ T019；T021 依赖 T020
- **Phase 5 (US3)**: T022 ~ T025 可并行；T026 依赖 T022 ~ T025；T027 依赖 T026
- **Phase 6 (US4)**: T028 独立可并行；T029 依赖 T028 和 US1 的 T014；T030 依赖 T029
- **Phase 7**: T031 ~ T036 可并行（不同文件）

### Recommended Execution Order

1. **Setup + Foundational**（T001 ~ T011）
2. **US1**（T012 ~ T015）→ 验证知识库闭环
3. **US2**（T016 ~ T021）→ 验证 RAG 对话
4. **US3 + US4 并行**（T022 ~ T030）→ 调研与置信度
5. **Polish**（T031 ~ T038）→ 导出导入、降级容错、归档压缩

---

## Notes

- `[P]` 标记的任务无文件冲突，可并行执行
- 每个用户故事的服务层实现应先完成 Pydantic 模型和相关基础设施
- 每次完成任务或任务组后应及时 `git commit`，保持小步提交
- 避免在未完成 Foundational 阶段时提前侵入用户故事实现
