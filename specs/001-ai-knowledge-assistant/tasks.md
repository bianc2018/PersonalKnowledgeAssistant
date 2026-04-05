# Tasks: AI 知识管理助手

**Input**: Design documents from `/specs/001-ai-knowledge-assistant/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 项目初始化与基础目录结构

- [ ] T001 创建项目目录结构：按 plan.md 建立 `src/` 及 `tests/` 下各子目录
- [ ] T002 初始化 Python 项目：创建 `pyproject.toml` 或 `requirements.txt`，安装 FastAPI、uvicorn、sqlite-vec、aiosqlite、httpx、pydantic-settings、cryptography、argon2-cffi、pytest、pytest-asyncio
- [ ] T003 [P] 配置代码格式与 Lint 工具（ruff / black / mypy）及 VS Code / EditorConfig

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 核心基础设施，必须在任何用户故事之前完成

**⚠️ CRITICAL**: 基础层未完成前，禁止开始任何用户故事实现

- [ ] T004 实现 SQLite + sqlite-vec 数据库连接与初始化：`src/db/connection.py`、`src/db/models.py`（含所有核心表结构）
- [ ] T005 实现数据库迁移框架：基础版本管理脚本（可简化为启动时自动 `CREATE TABLE IF NOT EXISTS` + 版本记录表）
- [ ] T006 [P] 实现单用户密码鉴权：`src/security/auth.py`（JWT 签发与校验）+ `src/security/crypto.py`（AES-256-GCM + Argon2id）
- [ ] T007 [P] 搭建 FastAPI 应用骨架：`src/main.py`（含路由注册、全局异常处理器、CORS、StaticFiles）
- [ ] T008 实现配置管理：`src/config.py`（Pydantic Settings，含 LLM、Embedding、搜索、隐私、重试、存储、日志配置）
- [ ] T009 实现日志基础设施：`src/utils/logging.py`（应用错误日志与关键操作日志输出到本地文件）
- [ ] T010 实现前端静态页面入口：`src/web/static/index.html` 与基础路由 `/`

**Checkpoint**: 基础框架就绪，应用可启动，数据库可连接，鉴权链路可跑通

---

## Phase 3: User Story 1 - 添加并管理个人知识 (Priority: P1) 🎯 MVP

**Goal**: 用户能够添加、浏览、搜索、删除（软删除）知识条目；支持标签和多格式附件，前端可查看列表与详情。

**Independent Test**: 用户在知识库页面添加一条文本知识，随后在列表中搜索关键词能命中该知识，查看详情时标题和内容正确。

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] 契约测试：`tests/contract/test_knowledge_api.py`（覆盖创建、列表、详情、更新、删除接口的输入输出契约）
- [ ] T012 [P] [US1] 集成测试：`tests/integration/test_knowledge_journey.py`（添加知识→搜索→查看详情→删除的完整流程）

### Implementation for User Story 1

- [ ] T013 [P] [US1] 实现标签模型：`src/db/models.py` 中 `Tag` 与 `TagLink` 的 CRUD 工具函数
- [ ] T014 [P] [US1] 实现知识库服务层：`src/services/knowledge_service.py`（知识 CRUD、版本管理、标签关联、软删除）
- [ ] T015 [P] [US1] 实现附件存储服务：`src/services/storage_service.py`（本地文件两级目录保存、加密读写、提取状态记录）
- [ ] T016 [P] [US1] 实现多媒体提取服务骨架：`src/services/extraction_service.py`（优先支持文本、PDF、Word、Excel、网页；图片 OCR 和音视频转录做接口预留）
- [ ] T017 [US1] 实现知识库 API：`src/api/routes/knowledge.py`（覆盖 `POST /api/knowledge`、上传、URL 添加、列表、详情、更新、删除、标签接口）
- [ ] T018 [US1] 实现前端知识库页面：`src/web/static/knowledge.html` / `knowledge.js`（列表、搜索、添加弹窗、详情展示）

**Checkpoint**: US1 独立可用，用户可完成“添加→搜索→查看→删除”闭环

---

## Phase 4: User Story 2 - 对话式查询知识 (Priority: P1) 🎯 MVP

**Goal**: 用户可就个人知识库内容发起自然语言对话，系统基于 RAG 检索生成回答并带来源引用；支持会话列表和历史继续。

**Independent Test**: 知识库中已存在一条关于“低空经济”的知识，用户在对话中问“低空经济有哪些政策支持？”，助手回答中必须引用该知识来源。

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T019 [P] [US2] 契约测试：`tests/contract/test_chat_api.py`（消息发送、流式与非流式响应格式、引用结构）
- [ ] T020 [P] [US2] 集成测试：`tests/integration/test_chat_rag.py`（先插入知识→发起对话→验证回答包含正确 citation）

### Implementation for User Story 2

- [ ] T021 [P] [US2] 实现 Embedding 服务：`src/services/embedding_service.py`（外部 OpenAI 兼容 API 封装，知识分片与向量写入 sqlite-vec）
- [ ] T022 [P] [US2] 实现检索服务：`src/services/embedding_service.py` 中增加混合检索（向量相似度 + FTS5 关键词召回）
- [ ] T023 [P] [US2] 实现 LLM 客户端：`src/ai/client.py`（兼容 OpenAI API，支持流式输出与工具调用接口）
- [ ] T024 [P] [US2] 实现对话生成服务：`src/services/chat_service.py`（组装 RAG 上下文、调用 LLM、解析 citation、处理无结果时的拒绝回答）
- [ ] T025 [P] [US2] 实现用户画像服务：`src/services/chat_service.py` 内画像更新逻辑，或独立 `src/services/profile_service.py`（基于对话历史提取兴趣与知识水平）
- [ ] T026 [US2] 实现对话 API：`src/api/routes/chat.py`（会话 CRUD、消息发送、SSE 流式响应 `/api/chat/conversations/{id}/messages`）
- [ ] T027 [US2] 实现前端对话页面：`src/web/static/chat.html` / `chat.js`（会话列表、消息展示、流式渲染、来源引用高亮）

**Checkpoint**: US2 独立可用，RAG 查询能正确引用知识库内容；无相关知识时拒绝编造

---

## Phase 5: User Story 3 - 生成领域调研报告 (Priority: P2)

**Goal**: 用户可提交调研主题，系统异步检索网络信息并生成结构化报告；页面通过 SSE 实时展示进度，遇到分支决策时暂停并向用户提问。

**Independent Test**: 用户提交“低空经济政策分析”主题，页面通过 SSE 看到进度更新；若系统提出决策问题，用户选择后调研继续，最终生成包含背景、关键观点、趋势、结论的报告。

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T028 [P] [US3] 契约测试：`tests/contract/test_research_api.py`（任务创建、SSE 事件类型、状态机流转、保存报告接口）
- [ ] T029 [P] [US3] 集成测试：`tests/integration/test_research_flow.py`（提交任务→模拟进度事件→完成报告→保存到知识库）

### Implementation for User Story 3

- [ ] T030 [P] [US3] 实现搜索源适配层：`src/ai/search.py`（统一 `SearchProvider` 接口，实现 LLM 自带搜索、Tavily/SerpAPI、httpx+trafilatura 爬虫三种适配器）
- [ ] T031 [P] [US3] 实现异步调研任务队列：`src/tasks/queue.py`（基于 asyncio Queue，按外部 API 配额控制并发，状态持久化到数据库）
- [ ] T032 [US3] 实现调研服务：`src/services/research_service.py`（分阶段执行：大纲→检索→章节撰写→汇总；支持暂停提问与恢复）
- [ ] T033 [US3] 实现调研 API：`src/api/routes/research.py`（任务提交、详情、SSE 进度订阅、用户决策回复、保存报告）
- [ ] T034 [US3] 实现前端调研页面：`src/web/static/research.html` / `research.js`（主题输入、进度条、SSE 事件展示、决策弹窗、报告预览与保存）

**Checkpoint**: US3 独立可用，异步调研全链路跑通，SSE 进度正常，人机决策可恢复

---

## Phase 6: User Story 4 - 知识置信度评估 (Priority: P2)

**Goal**: 系统对每个知识版本自动进行置信度评分，界面上可视化展示评分与依据；支持手动触发重新评估，且历史版本的评估结果独立保留。

**Independent Test**: 用户上传一条带有事实性陈述的知识，保存后系统自动完成评估，详情页显示“高/中/低”评分及依据说明；用户修改内容后触发新版本并自动重新评估，旧版本评估记录不变。

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T035 [P] [US4] 契约测试：`tests/contract/test_confidence_api.py`（评估触发接口、评分返回结构）
- [ ] T036 [P] [US4] 集成测试：`tests/integration/test_confidence_flow.py`（添加知识→自动评估→修改触发新版本→验证旧版本评估不变）

### Implementation for User Story 4

- [ ] T037 [P] [US4] 实现置信度评估服务：`src/services/confidence_service.py`（调用 LLM 进行网络验证或常识推理，输出 score_level、method、rationale）
- [ ] T038 [P] [US4] 在知识库服务中集成自动评估触发：`src/services/knowledge_service.py` 保存/更新后，若内容变化 >20% 则异步调用置信度评估
- [ ] T039 [US4] 实现置信度评估 API：`src/api/routes/knowledge.py` 中增加 `POST /api/knowledge/{id}/evaluate-confidence` 手动触发端点
- [ ] T040 [US4] 前端展示置信度：`src/web/static/knowledge.js` 中在列表和详情页渲染评分徽章与依据弹窗

**Checkpoint**: US4 独立可用，自动评估与手动评估均正常工作，历史版本评估隔离

---

## Phase 7: System & Cross-Cutting Concerns

**Purpose**: 系统级功能与跨用户故事的增强

- [ ] T041 [P] 实现系统配置 API：`src/api/routes/system.py`（状态、配置读写、隐私策略开关）
- [ ] T042 [P] 实现导出功能：`src/api/routes/system.py` 导出 ZIP（含 metadata.json、原始附件，不含 embedding 向量）
- [ ] T043 [P] 实现导入功能：`src/api/routes/system.py` 导入 ZIP（校验 JSON、跳过损坏文件、模型不一致时重算向量）
- [ ] T044 实现降线与容错机制：外部 AI/搜索请求的自动重试（指数退避 3 次）、服务不可用提示、本地模型降级逻辑
- [ ] T045 实现磁盘归档压缩：`src/services/storage_service.py` 中容量超过阈值时对旧媒体文件 gzip 归档
- [ ] T046 [P] 补充单元测试：`tests/unit/` 覆盖核心服务函数的纯逻辑分支
- [ ] T047 [P] 运行时验证：按 `quickstart.md` 完整走通安装→启动→添加知识→对话→调研→导出流程

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → 无依赖，可立即开始
- **Foundational (Phase 2)** → 依赖 Setup 完成 → **阻塞所有用户故事**
- **User Stories (Phase 3-6)** → 均依赖 Foundational 完成；US1 → US2 → US3/US4 可按优先级顺序或并行推进
- **System (Phase 7)** → 依赖基本用户故事稳定后实施

### User Story Dependencies

| Story | 前置依赖 | 说明 |
|-------|----------|------|
| US1 (P1) | Foundational | 无其他故事依赖 |
| US2 (P1) | Foundational + US1 的数据层 | 需要知识库中已有知识才能做 RAG 验证；技术上可并行开发，但集成测试需 US1 接口可用 |
| US3 (P2) | Foundational + US1 数据层 | 调研报告保存到知识库依赖 US1 的入库能力 |
| US4 (P2) | Foundational + US1 | 置信度评估依赖知识版本模型 |

### 推荐实现顺序

1. **Setup + Foundational**（T001 ~ T010）
2. **US1**（T011 ~ T018）→ 验证知识库闭环
3. **US2**（T019 ~ T027）→ 验证 RAG 对话
4. **US3 + US4 并行**（T028 ~ T040）→ 调研与置信度
5. **System + Polish**（T041 ~ T047）→ 导出导入、降级容错、归档压缩

---

## Notes

- `[P]` 标记的任务无文件冲突，可并行执行。
- 每个用户故事内部：模型/服务层先于 API/前端实现；测试先于实现编写。
- 每次完成任务或任务组后应及时 `git commit`，保持小步提交。
- 避免在未完成 Foundational 阶段时提前侵入用户故事实现。
