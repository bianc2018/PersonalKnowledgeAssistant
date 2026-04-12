# 003-web-frontend 代码库分析

> 分析日期: 2026-04-10  
> 目标: 为 PersonalKnowledgeAssistant（AI 个人知识助手）的现有 FastAPI 服务设计并开发 Web 前端页面，覆盖全部已有 API 功能。

---

## 1. 项目结构与已有目录总览

```
/home/myhql/code/PersonalKnowledgeAssistant
├── src/
│   ├── main.py                 # FastAPI 入口 + 静态文件挂载 + 路由注册
│   ├── config.py               # Pydantic Settings + 环境变量管理
│   ├── auth/                   # JWT/Argon2id + master key 缓存
│   ├── chat/                   # 对话模型/路由/服务（含 SSE Streaming）
│   ├── knowledge/              # 知识 CRUD、文件上传、URL 抓取、标签、版本、置信度
│   ├── research/               # 调研任务 CRUD + Worker + SSE 进度推送
│   ├── system/                 # 系统初始化、配置、导入/导出、重置
│   ├── profile/                # 用户画像自动更新（基于对话）
│   ├── search/                 # sqlite-vec + FTS5 混合检索
│   ├── external/               # LLM / Search / Retry 封装
│   ├── tasks/queue.py          # 内存队列 + 并发控制 + SSE 订阅
│   ├── db/                     # aiosqlite 连接 + schema.sql
│   ├── web/                    # 已有的静态文件/模板目录（目前为空）
│   │   ├── static/             # 空
│   │   └── templates/          # 空
│   └── utils.py                # 通用工具
├── tests/
│   ├── conftest.py             # pytest-asyncio + AsyncClient fixture
│   └── integration/            # auth_system / chat / knowledge / research / deploy e2e
├── specs/001-ai-knowledge-assistant/
│   ├── contracts/              # api-overview / chat / knowledge / research / system API 契约
│   ├── data-model.md
│   ├── spec.md
│   └── plan.md
├── requirements.txt            # FastAPI + uvicorn[standard] + sqlite-vec + aiosqlite + httpx + pydantic-settings + python-jose + python-multipart + 多媒体提取库 + openai
├── deploy.py                   # 一键部署脚本
└── .env                        # 环境变量配置
```

---

## 2. 现有 Web 基础设施分析

### 2.1 静态文件与模板服务
- **`src/main.py`** 已配置 `StaticFiles`，挂载点：
  - `static_dir = PROJECT_ROOT / "src" / "web" / "static"`
  - `app.mount("/static", StaticFiles(directory=static_dir), name="static")`
- 根路径 `/` 的 `root()` 已尝试返回 `static_dir / "index.html"`，否则返回 JSON 提示服务运行中。
- **当前状态**：`static/` 与 `templates/` 均为空目录。没有启用 `Jinja2Templates`，也没有其他模板引擎配置。

### 2.2 CORS 配置
- 已全局开启 `CORSMiddleware`，`allow_origins=["*"]`，允许外部 SPA 在开发模式下跨域调用。但生产环境 Web 前端与服务同域部署，更推荐直接挂载。

### 2.3 异常处理
- 全局 `@app.exception_handler(Exception)` 捕获未处理异常，返回 500 + `{"detail": "服务器内部错误，请稍后重试"}`。

---

## 3. 现有 API 端点完整清单

所有端点以 `/api` 为前缀，已在 `src/main.py` 中统一 include_router。

### 3.1 认证 (Auth)
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/auth/login` | 登录，返回 JWT + expires_in | 公开 |

依赖文件：`src/auth/router.py`、`src/auth/dependencies.py`
- 使用 `HTTPBearer` 提取 `Authorization: Bearer <token>`。
- `get_current_user` 校验 JWT（HS256，secret_key 来自 settings），同时检查 token 是否存在于内存 master key 缓存中（logout 可清除）。
- 登录成功后缓存 master key（用于后续文件加密/解密）。

### 3.2 系统 (System)
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/system/init` | 系统初始化，设置管理员密码 | 公开 |
| GET  | `/api/system/status` | 获取初始化状态、LLM 连接状态、知识数量、存储占用 | 公开 |
| GET  | `/api/system/config` | 获取配置（API Key 已掩码） | 需要 Bearer |
| PUT  | `/api/system/config` | 更新配置 | 需要 Bearer |
| POST | `/api/system/export` | 导出加密备份（二进制流） | 需要 Bearer |
| POST | `/api/system/import` | 导入加密备份（multipart） | 需要 Bearer |
| POST | `/api/system/reset` | 重置系统（清数据、清文件） | 需要 Bearer |

依赖文件：`src/system/router.py`、`src/system/service.py`

### 3.3 知识库 (Knowledge)
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/knowledge` | 创建文本知识 | 需要 Bearer |
| POST | `/api/knowledge/upload` | 上传文件创建知识（multipart，≤1GB） | 需要 Bearer |
| POST | `/api/knowledge/url` | 添加 URL 知识 | 需要 Bearer |
| GET  | `/api/knowledge` | 知识列表（分页、关键词、标签过滤、软删除） | 需要 Bearer |
| GET  | `/api/knowledge/tags` | 标签列表 | 需要 Bearer |
| GET  | `/api/knowledge/{item_id}` | 知识详情（含版本、附件、标签、置信度） | 需要 Bearer |
| PATCH| `/api/knowledge/{item_id}` | 更新知识（内容变化 >20% 自动创建新版本） | 需要 Bearer |
| DELETE| `/api/knowledge/{item_id}` | 软删除 | 需要 Bearer |
| POST | `/api/knowledge/{item_id}/evaluate-confidence` | 手动触发置信度评估 | 需要 Bearer |

**注意**：契约中提到了 `/api/knowledge/{id}/attachments/{attachment_id}/download` 下载端点，但在当前代码（`src/knowledge/router.py`）中暂未实现，是前端需要覆盖的潜在新增需求。

依赖文件：`src/knowledge/router.py`、`src/knowledge/service.py`、`src/knowledge/models.py`

### 3.4 对话 (Chat)
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET  | `/api/chat/conversations` | 会话列表（分页） | 需要 Bearer |
| POST | `/api/chat/conversations` | 创建新会话 | 需要 Bearer |
| GET  | `/api/chat/conversations/{id}/messages` | 获取会话消息 | 需要 Bearer |
| POST | `/api/chat/conversations/{id}/messages` | 发送消息（`stream=true` 时返回 SSE） | 需要 Bearer |

**SSE 事件类型**（Chat）：delta / citation / done / error
依赖文件：`src/chat/router.py`、`src/chat/service.py`、`src/chat/models.py`

### 3.5 调研 (Research)
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/research` | 提交调研任务 | 需要 Bearer |
| GET  | `/api/research` | 调研任务列表（分页） | 需要 Bearer |
| GET  | `/api/research/{task_id}` | 调研任务详情 | 需要 Bearer |
| GET  | `/api/research/{task_id}/events` | SSE 订阅任务进度/状态/问题 | 需要 Bearer |
| POST | `/api/research/{task_id}/respond` | 提交用户决策，恢复任务 | 需要 Bearer |
| POST | `/api/research/{task_id}/save` | 保存调研报告到知识库 | 需要 Bearer |

**SSE 事件类型**（Research）：status / progress / chunk / question / report / error
依赖文件：`src/research/router.py`、`src/research/service.py`、`src/research/worker.py`、`src/research/models.py`、`src/tasks/queue.py`

---

## 4. Web 前端集成点分析

### 4.1 最小侵入式集成方案
已有的 FastAPI 服务已预留 `src/web/static/` 和 `src/web/templates/` 目录，且 `/static` 已挂载。根路径 `/` 也已尝试返回 `index.html`。

**推荐方案**：在 `src/web/static/` 放置一个单页应用（SPA）产物（纯 HTML/CSS/JS，无额外构建依赖），直接由 FastAPI 现有的 `StaticFiles` 和 `FileResponse` 服务。

### 4.2 路由冲突分析
- API 路由均集中在 `/api/*`。
- 静态文件挂载在 `/static/*`。
- 根路径 `/` 返回 `index.html`。
- **无冲突**：SPA 的前端路由（hash 模式或 history 模式）不会与后端 API 路径冲突。若使用 HTML5 history 模式，仅需确保前端刷新时服务端仍返回 `index.html`; FastAPI 当前 `root()` 只处理 `/`，需要在规划阶段决定是否扩展 catch-all（如 `/{path:path}`）来支持 history 模式。

### 4.3 认证集成
- 前端需在登录页收集密码，调用 `POST /api/auth/login` 获取 token。
- 将 token 保存在 `sessionStorage` 或 `localStorage`（后者对应“记住我”长周期）。
- 所有受保护请求在 Header 中携带 `Authorization: Bearer <token>`。
- 401 响应触发重新登录。
- **注意**：后端在 `get_current_user` 中除了验证 JWT，还检查 `get_cached_master_key(token)` 是否存在。服务端重启后缓存清空，此时旧 token 即使未过期也会 401。前端必须能够处理此情况并引导重新登录。

### 4.4 SSE 消费
- **聊天 SSE**：`POST /api/chat/conversations/{id}/messages`（`stream=true`）
  - 返回 `text/event-stream`，事件类型：delta、 citation、 done、 error。
- **调研 SSE**：`GET /api/research/{task_id}/events`
  - 返回 `text/event-stream`，事件类型：status、 progress、 chunk、 question、 report、 error。
- 前端需要统一的 `EventSource` 封装，支持自动重连（推荐原生 `EventSource` 或轻量封装）。注意：`EventSource` 不支持自定义 Header，因此传递 Bearer token 有两种方式：
  1. 将 token 放在 URL query 参数（`?token=...`）—— 需要后端配合修改。
  2. 使用 `fetch` + `ReadableStream` 手动解析 SSE，这样可以在 Header 中携带 token。
  - **当前后端未支持 query token**。若前端使用原生 `EventSource`，需要在集成端点中为 SSE 路由增加 `?token=` 支持，或前端手动 fetch stream。设计方案时必须明确这一点。

### 4.5 文件上传与下载
- **上传**：`POST /api/knowledge/upload` 使用 `multipart/form-data`，前端需要文件选择组件 + `FormData`。
- **下载**：当前后端缺少附件下载路由。前端若需要“查看/下载原始文件”，需要后端补充 `/api/knowledge/{item_id}/attachments/{attachment_id}/download`（返回解密后二进制流）。
- **导出**：`POST /api/system/export` 返回二进制流，前端需触发浏览器下载（`Blob` + `URL.createObjectURL` + `<a>`）。
- **导入**：`POST /api/system/import` 同样使用 `multipart/form-data`。

---

## 5. 技术复杂度评估

### 5.1 前端架构选项

| 选项 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **纯 HTML/CSS/JS (SPA)** | 无构建工具依赖，直接放入 `static/`；与现有 Python 项目风格一致（极简） | 无组件复用、状态管理需手写 | 高（适合 MVP 与现有项目风格） |
| **Jinja2 + HTMX** | 服务端渲染，SEO 友好 | 需要为几乎每个页面写模板和路由，增加后端复杂度；SSE 和流式交互仍需较多 JS | 中 |
| **现代前端框架 (Vue/React)** | 组件化、生态丰富 | 需要 Node.js 构建链、与当前纯 Python 仓库风格不符 | 低（ unless 产品明确要求） |

**建议**：MVP 阶段选择**纯 HTML/CSS/JS 单页应用**，利用原生 `fetch`、`EventSource`（或手动 stream）、`history.pushState` 实现。与现有技术栈（纯 Python、无 Node）保持一致。

### 5.2 需要新增/修改的目录和文件

#### 前端资源（无需改动后端即可工作）
```
src/web/static/
├── index.html          # 入口（登录页或应用壳）
├── css/
│   └── app.css         # 全局样式
└── js/
    ├── api.js          # 封装所有 API 调用
    ├── auth.js         # 登录状态管理
    ├── router.js       # 简单前端路由
    ├── sse.js          # SSE 统一封装（fetch stream）
    ├── app.js          # 主入口
    └── pages/          # 各页面逻辑
        ├── login.js
        ├── dashboard.js
        ├── knowledge.js
        ├── chat.js
        ├── research.js
        └── settings.js
```

#### 后端需要补充的路由/能力
1. **附件下载端点**：`GET /api/knowledge/{item_id}/attachments/{attachment_id}/download`
   - 需要读取 attachments 表获取 `storage_path` 和 `mime_type`。
   - 使用 `get_cached_master_key(token)` 解密文件后返回 `StreamingResponse` 或 `FileResponse`。
   - 若不实现，前端无法提供原始文件下载/预览。
2. **SPA history 模式支持**（可选）：
   - 增加 `@app.get("/{path:path}")` 或专门的前端路由回退，确保非根路径刷新时返回 `index.html`，而不是 404。
3. **SSE token 传递支持**（可选但强烈建议）：
   - 为 `GET /api/research/{task_id}/events` 和聊天 SSE 增加 query parameter `?token=` 校验支持，兼容原生 `EventSource`。
   - 或决定前端使用 fetch stream 手动解析 SSE。

---

## 6. 代码库约束（Spec 和 Plan 必须遵守）

### 6.1 单用户架构约束
- 没有用户注册、多用户隔离、RBAC。
- `system_config` 和 `user_profiles` 表均固定 `id = 1`。
- 前端不应出现“用户管理”、“注册”、“权限分配”等多用户概念。

### 6.2 认证与加密约束
- 密码规则：≥8 位，必须同时包含英文字母和阿拉伯数字（`system/router.py` 中硬编码校验）。
- 所有受保护端点必须携带 `Authorization: Bearer <token>`。
- 服务端重启后 token 对应的 master key 缓存丢失，旧 token 会 401，前端必须引导重新登录。

### 6.3 数据存储约束
- 所有核心数据存在 SQLite（`settings.database_url`），向量检索依赖 `sqlite-vec`。
- 文件存储在本地文件系统 `files/AB/CD/<item-id>/` 两级目录下，且文件经过 AES-256-GCM 加密。
- 前端不应尝试直接访问文件系统，所有文件操作必须通过 API。

### 6.4 状态与异步任务约束
- Research Worker 使用内存队列（`src/tasks/queue.py`），没有持久化消息队列。
- SSE 进度推送也基于内存中的 `asyncio.Queue`，服务端重启后所有任务状态可能停留在 `pending_recheck` 或原状态，前端需要能接受 SSE 断线重连。
- 调研任务在 `awaiting_input` 状态不设自动超时，前端需要一直等待用户决策。

### 6.5 第三方服务依赖
- LLM 和 Embedding 均通过 OpenAI 兼容接口调用（`openai.AsyncOpenAI`），配置存储在数据库。
- 若 LLM 不可用，系统进入“降级模式”，`chat_completion` 返回固定降级文案：`【降级模式】当前 LLM 服务不可用，请检查配置或网络连接后重试。`
- 前端需要能够展示系统状态（`llm_connected`、`embedding_available`、`search_source_available`）并引导用户配置。

### 6.6 版本与测试约束
- Python 版本 3.11+。
- 测试使用 `pytest-asyncio` + `httpx.AsyncClient(ASGITransport)`，已有完整集成测试套件。
- 新增后端路由必须配套集成测试（遵循现有 `tests/integration/` 风格）。

---

## 7. 对规划阶段的实现指导

### 7.1 Spec 文档中应明确的范围
1. **前端类型**：纯 HTML/CSS/JS SPA，无构建工具，产物直接放在 `src/web/static/`。
2. **页面清单**：
   - 登录页（`/login` 或模态框）
   - 初始化引导页（首次使用）
   - Dashboard / 首页（系统状态概览）
   - 知识库页（列表、搜索、标签过滤、新建/编辑/删除、详情 drawer）
   - 对话页（会话列表、消息列表、流式回复、引用展示）
   - 调研页（任务列表、新建任务、详情 + SSE 进度、决策弹窗、保存报告）
   - 设置页（LLM / Embedding / Search / Privacy / Storage / Log 配置、导出/导入/重置）
3. **路由策略**：hash 模式（最简单，无需后端 catch-all） vs history 模式（需后端配合）。建议 MVP 使用 hash 模式。
4. **SSE 策略**：明确前端使用 `fetch` + `ReadableStream` 手动解析 SSE，避免后端修改 token 传递方案；或在后端为 SSE 增加 query token 支持并在 spec 中说明。
5. **文件下载**：必须在 spec 中要求后端补充附件下载 API，否则前端无法完整支持文件型知识。

### 7.2 Plan 文档中应包含的关键任务
1. 补充后端路由
   - `GET /api/knowledge/{item_id}/attachments/{attachment_id}/download`
   - （可选）SSE query token 支持 或 catch-all 前端路由
2. 前端框架/结构搭建
   - `src/web/static/index.html`
   - `src/web/static/js/api.js` 封装所有 API
   - `src/web/static/js/router.js` 简单 hash 路由
   - `src/web/static/js/sse.js` 基于 fetch 的 SSE 解析器
   - 各页面组件（Dashboard / Knowledge / Chat / Research / Settings）
3. 页面逐一实现
   - 登录与初始化（含错误提示、密码强度校验）
   - 系统 Dashboard（状态卡片 + 快捷入口）
   - 知识库（CRUD + 搜索 + 标签 + 分页 + 上传 + URL 添加）
   - 对话（会话切换、消息历史、SSE 流式渲染、引用高亮）
   - 调研（任务列表、SSE 进度条、决策问答、报告保存）
   - 设置（配置表单、导出/导入/重置操作确认）
4. 集成测试
   - 按照现有 `tests/integration/` 风格，为新增后端 API 写测试。
   - （可选）使用 Playwright 或 pytest 做前端端到端测试，但考虑到纯静态 SPA 且当前无 Node，建议先以手工 QA 为主。

### 7.3 技术与设计建议
- **样式库**：为了零构建，可引入 CDN 版本的轻量 CSS 框架，如 **Tailwind CSS CDN** 或 **Pico CSS**，快速实现现代化界面。
- **图标**：使用inline SVG或 CDN 引入 `phosphor-icons` / `lucide` IIFE 版本。
- **状态管理**：无需 Redux/Vuex。利用一个简单的全局 `state` 对象 + 自定义事件分发即可。
- **代码组织**：按功能拆分为 `pages/` 子目录，`api.js` 集中管理所有 fetch 和错误处理逻辑。
- **安全性**：前端不存储密码，仅存储 JWT；导出/导入/重置等危险操作需二次密码确认弹窗。

---

## 8. 待确认事项（供 Product Spec 阶段决策）

1. 前端是否采用 hash 路由以完全避免后端 catch-all 修改？
2. SSE 采用原生 `EventSource`（需后端增加 query token）还是 fetch stream（前端复杂一点）？
3. 是否需要后端立即补充附件下载 API？（建议选“是”，否则文件型知识不完整）
4. 是否引入 CDN CSS 框架？若否，手写 CSS 量较大。
5. 是否需要为 Web 前端新建 pytest 测试（如使用 Playwright/Selenium），还是只测后端 API？
