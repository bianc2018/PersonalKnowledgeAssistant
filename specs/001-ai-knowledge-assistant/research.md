# Phase 0 Research: AI 知识管理助手

> 生成日期: 2026-04-05 | 关联 Spec: [spec.md](./spec.md) | 关联 Plan: [plan.md](./plan.md)

---

## 1. 技术栈总览决策

**Decision**: 采用 Python 3.11+ + FastAPI 构建本地单用户 Web 服务。

**Rationale**:
- Python 在 AI/LLM 生态中库支持最完善，OpenAI API、向量检索、加密原语均有成熟封装。
- FastAPI 原生支持异步路由、SSE、依赖注入和 Pydantic 校验，能够以最小依赖满足 Web 服务、实时推送和自动文档需求。
- 单仓库、单后端进程即可承载全部需求，无需拆分为前后端分离的多工程结构。

**Alternatives considered**:
- Node.js + Express：AI SDK 丰富度不及 Python，且SQLite/向量扩展生态较弱。
- Rust + Axum：性能更优，但开发周期更长，多媒体处理库不如 Python 成熟，对 MVP 而言过度。

---

## 2. 数据库与向量检索

**Decision**: 使用 SQLite 作为主存储，通过 `sqlite-vec` 扩展实现向量与全文检索。

**Rationale**:
- Spec 明确要求 SQLite + sqlite-vec，且 sqlite-vec 作为 SQLite 的 C 扩展，以 `sqlite-vec` PyPI 包可直接在 Python 中加载使用。
- 单用户本地场景下无需 PostgreSQL/pgvector 或独立向量数据库，避免运维复杂度。
- sqlite-vec 同时支持 `vec0` 虚拟表（向量）和 FTS5（全文），能够满足 RAG 的混合检索需求。

**Implementation notes**:
- 使用 `sqlite_vec.load(db)` 在连接时加载扩展。
- 向量表与业务表分离：业务表存储 KnowledgeItem 元数据，向量表仅存储 `item_id`、`chunk_text`、`embedding`。
- 全文搜索与向量搜索可并行执行后合并排序，或用简单的“先向量召回再全文过滤”策略，MVP 阶段无需引入复杂重排序模型。

---

## 3. 异步调研任务与 SSE 推送

**Decision**: 使用 FastAPI `BackgroundTasks` + 内存中的 `asyncio.Queue` 实现调研任务队列，通过 SSE 向客户端推送进度。

**Rationale**:
- 调研任务具有“长时运行 + 可中断/人机交互”的特点，但并发量受限于外部 API 配额，本地单用户场景下任务峰值极低。
- 引入 Celery/RabbitMQ/Redis 会显著增加部署和依赖复杂度，违反“简洁设计”原则。
- `asyncio.Queue` 足以实现按API配额控制并发（如同时最多2个调研任务），其余任务排队等待。

**Implementation notes**:
- `/api/research` POST 接收主题，创建任务记录并推入队列，立即返回任务 ID。
- `/api/research/{id}/events` SSE 端点订阅任务状态变更，推送 `progress`、`chunk`、`question`、`completed`、`error` 等事件。
- 后台工作协程从队列取出任务，分阶段执行（大纲生成→信息检索→章节撰写→汇总输出），每阶段更新任务状态并触发 SSE。
- 遇到需要用户决策的节点时，任务状态置为 `awaiting_input`，SSE 推送 `question` 事件；用户通过 `/api/research/{id}/respond` 提交决策后恢复队列处理。

**Alternatives considered**:
- Celery + Redis：功能强大，但需要额外运行 Redis，部署复杂度不适合本地单用户应用。
- 纯线程池：无法很好地与 FastAPI 的异步生态整合，且 SSE 推送不如 asyncio 原生简洁。

---

## 4. LLM 与搜索源集成

**Decision**:
- LLM 调用：使用 `openai` 官方 Python SDK（兼容任意 OpenAI API 端点，通过配置 `base_url` 和 `api_key` 切换服务商）。
- 搜索优先级：
  1. 检测模型是否声明支持 `web_search` 工具（通过配置项或模型标识判断），若支持则在 LLM 调用中启用。
  2. 否则回退至用户配置的独立搜索 API（Tavily、SerpAPI 等兼容端点，统一封装为 `SearchProvider` 接口）。
  3. 若仍不可用，使用内置轻量 HTTP 爬虫（基于 `httpx` + `trafilatura`）抓取网页正文。

**Rationale**:
- `openai` SDK 是 OpenAI API 兼容性最好的封装，同时支持流式响应（stream），适用于对话生成和调研报告流式输出。
- 将搜索能力抽象为 `SearchProvider` 接口，可方便地扩展新的搜索源，保持代码整洁。
- `trafilatura` 是专门用于提取网页正文的库，比 `beautifulsoup4` 更鲁棒，且依赖较少。

**Implementation notes**:
- 配置文件中增加 `llm` 和 `search` 两个配置块：
  - `llm.base_url`、`llm.api_key`、`llm.model`、`llm.enable_search`
  - `search.provider`、`search.api_key`、`search.base_url`
- 界面通过 `/api/system/status` 返回当前激活的搜索源类型（`llm_builtin`、`search_api`、`http_crawler`、`unavailable`）。

**Alternatives considered**:
- 直接使用 `httpx` 手动构造请求：可减少一个依赖，但需要自行处理流式解析、错误重试、工具调用等，维护成本高于使用 SDK。
- 使用 LangChain：功能强大但引入了过于庞大的抽象层和额外依赖，不符合 MVP 的简洁要求。

---

## 5. 多媒体文本提取方案

**Decision**: 分阶段支持多媒体提取，MVP 阶段优先覆盖文本和常见文档，图片 OCR 和音视频转录作为次要支持项。

| 媒体类型 | 提取方案 | 说明 |
|---------|---------|------|
| 纯文本 / Markdown | 直接入库 | 无额外依赖 |
| PDF | `pypdf` | 轻量、纯 Python，满足基础文本提取 |
| Word (.docx) | `python-docx` | 轻量、纯 Python |
| Excel (.xlsx) | `openpyxl` | 轻量、纯 Python |
| 图片 OCR | `pytesseract` (+ `Pillow`) | 需系统安装 Tesseract OCR 引擎；若不可用则标记提取失败 |
| 音频/视频转录 | `faster-whisper` 或 Whisper API | 本地模型体积大，MVP 优先尝试外部 API；若本地模型已配置则回退使用 |
| 网页链接 | `httpx` + `trafilatura` | 提取正文后按文本处理 |

**Rationale**:
- MVP 阶段的需求是“自动提取非文本媒体为可搜索文本”，但实际技术栈中音视频本地转录模型（如 Whisper）会引入数百 MB 甚至数 GB 的模型文件，显著增加安装包体积和首次使用门槛。
- 优先保证文本、常见办公文档和网页链接的提取体验，图片 OCR 在有 Tesseract 环境时启用，音视频转录优先使用外部 API（若用户允许），本地模型作为可选项。
- 提取失败时，按 spec 要求保存原始文件、标记失败状态，并用文件名/扩展名做极简索引。

**Alternatives considered**:
- 统一使用 `unstructured` 库：功能全面但依赖极重，安装和部署复杂，不适合本地个人应用。
- 所有媒体本地处理：会导致安装包过大，与“简洁设计”和“本地优先”的平衡冲突。

---

## 6. 加密与鉴权方案

**Decision**: 采用 `cryptography`（AES-256-GCM）+ `argon2-cffi`（Argon2id）实现本地数据加密和单用户密码鉴权。

**Rationale**:
- Spec 明确要求 AES-256-GCM + Argon2id，`cryptography` 和 `argon2-cffi` 是 Python 生态中经过审计、广泛使用的标准库。
- 单用户场景下无需引入 OAuth、LDAP 等外部认证系统，本地密码派生密钥即可满足需求。

**Implementation notes**:
- **密钥派生**：用户首次设置密码时，使用 Argon2id 生成一个主密钥（master key），并生成一个随机的 salt 存储于本地。
- **数据加密**：原始媒体文件按分块读取，使用 AES-256-GCM 加密后写入 `files/AB/CD/<item-id>/original.jpg.enc`，同时将 nonce 和 tag 与文件关联存储（或存储于数据库元数据中）。
- **鉴权**：用户登录时校验密码派生出的主密钥是否匹配预存的验证摘要；通过鉴权后，将主密钥缓存于内存（或短期 session）中，用于后续的文件加解密操作。
- **安全边界**：未登录时，系统不得以任何形式解密原始数据；数据库元数据（如标题、摘要）可存储于未加密的数据库中，但原始内容和附件必须加密。

---

## 7. Embedding 模型选择

**Decision**: 默认使用外部兼容 OpenAI API 的 Embedding 端点；若用户未配置或选择本地模式，可选降级至 `sentence-transformers`（需用户自行安装相关依赖）。

**Rationale**:
- 本地 embedding 模型（如 `all-MiniLM-L6-v2`）需要将模型文件（约 80MB+）和 `torch`/`onnxruntime` 打包，显著增加安装体积和启动时间。
- MVP 阶段以“快速可用”为首要目标，外部 API 是工作量最小的方案；同时保留本地模型的扩展接口，满足完全离线的用户需求。
- 导入时若 embedding 模型标识与当前配置不一致，按 spec 要求自动重新计算向量。

**Implementation notes**:
- 配置项 `embedding.base_url`、`embedding.api_key`、`embedding.model`。
- 本地模式通过统一的 `EmbeddingService` 接口封装，未来可通过 `sentence-transformers` 或 `onnxruntime` 实现，MVP 阶段先做接口预留和外部 API 实现。

**Alternatives considered**:
- 强制本地 embedding：虽然满足完全离线，但会显著增加项目依赖和安装复杂度，不符合 MVP 的最小必要原则。

---

## 8. 前端架构

**Decision**: MVP 前端采用纯静态 HTML + Vanilla JS（或 petite-vue / Alpine.js），由 FastAPI `StaticFiles` 直接托管，不引入独立前端构建流程。

**Rationale**:
- 产品形态为本地单用户 Web 应用，功能以表单、列表、对话窗口、报告展示为主，交互复杂度不高。
- 引入 React/Vue 构建工具链会额外增加 Node.js、npm、构建脚本等依赖，与“简洁设计”和“本地易部署”的目标冲突。
- 使用轻量 JS 框架或原生 JS 即可实现 SSE 订阅、对话流式渲染、文件上传和进度展示。

**Implementation notes**:
- `src/web/static/` 存放 HTML、CSS、JS 文件。
- `src/web/templates/` 存放 Jinja2 模板（如有需要）。
- `/` 路由重定向到 `index.html`。

---

## 9. 测试策略

**Decision**: 使用 `pytest` + `pytest-asyncio` + `httpx`（`AsyncClient`）进行单元和集成测试。

**Rationale**:
- FastAPI 官方推荐使用 `httpx.AsyncClient` 进行 ASGI 应用的集成测试，无需启动真实 HTTP 服务器。
- `pytest-asyncio` 支持异步测试用例，与 FastAPI 的异步路由无缝兼容。
- 外部 AI 和搜索服务在测试中使用 `respx`（httpx 的 mock 库）或 `unittest.mock` 进行模拟，避免测试依赖真实 API 配额。

**Implementation notes**:
- 单元测试覆盖 `services/` 和 `security/` 中的纯逻辑函数。
- 集成测试覆盖 `api/routes/` 中的路由，使用内存数据库或测试专用 SQLite 文件。
- 契约测试验证 `ai/search.py` 中各搜索 provider 的返回数据结构。

---

## 10. 降线与容错策略

**Decision**:
- 外部 AI/搜索请求失败：默认自动重试 3 次，指数退避（1s → 2s → 4s）；最终失败后向用户返回明确错误信息。
- 外部服务不可用时：本地知识库管理（增删改查）和对话查询保持可用；若配置了本地 LLM，调研降级至本地模型并提示用户；否则暂停调研任务并提示受限。
- 外部服务恢复后，处于 `pending_recheck` 状态的调研任务自动重新执行并推送更新。

**Rationale**:
- 保持本地核心功能可用是“本地优先”产品的基本要求。
- 指数退避重试是 HTTP 请求的标准容错模式，能有效减少瞬时网络波动导致的失败。
- 配置项暴露 `retry_times`、`retry_backoff`、`timeout`，满足 spec 要求的可配置性。

---

## 11. 总结

本研究阶段已解决 plan.md Technical Context 中的所有不确定性，确认以下关键技术选择：

1. **语言/框架**：Python 3.11+ + FastAPI
2. **数据库/向量**：SQLite + sqlite-vec
3. **异步任务**：asyncio Queue + BackgroundTasks + SSE
4. **LLM 客户端**：openai SDK
5. **搜索源**：LLM 自带搜索 → Tavily/SerpAPI → httpx + trafilatura 爬虫
6. **多媒体提取**：pypdf / python-docx / openpyxl / pytesseract（按需）/ faster-whisper（可选本地）
7. **加密鉴权**：cryptography (AES-256-GCM) + argon2-cffi (Argon2id)
8. **Embedding**：默认外部 API，可扩展本地模型
9. **前端**：静态 HTML/JS 由 FastAPI 托管
10. **测试**：pytest + pytest-asyncio + httpx + respx

无剩余 NEEDS CLARIFICATION。
