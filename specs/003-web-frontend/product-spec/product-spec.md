# Product Spec: Web 前端页面开发

> Status: DRAFT | Version: 1.0 | Date: 2026-04-10
> Feature: `003-web-frontend` | Size: Small
>
> **Related documents:** [User Journey](./user-journey.md) | [Wireframes](./wireframes/) | [Metrics](./metrics.md) | [Research →](../research/README.md)

---

## 1. Overview

### Problem Statement

PersonalKnowledgeAssistant 的后端 API（`001-ai-knowledge-assistant`）已经完整实现了知识库管理、对话式 RAG 查询、异步领域调研、系统设置等全部能力。然而，当前服务仅通过 REST API 和 Swagger 文档暴露功能，用户必须依赖 curl 或第三方 HTTP 客户端才能与系统交互。这极大地限制了产品的可用性和用户采纳：

- **高门槛**：非技术用户无法使用命令行调用 API。
- **体验割裂**：curl 无法呈现流式 SSE 聊天或调研进度追踪所带来的实时反馈。
- **功能浪费**：文件上传、导出/导入、会话历史浏览等操作在终端中极为繁琐，导致后端能力无法被充分利用。

没有一个统一、简洁的 Web 界面，产品的核心价值无法直接触达最终用户。

### Solution Summary

为现有 FastAPI 服务挂载一个零 Node 依赖的轻量 Web 前端。前端以 Jinja2 模板为页面骨架，HTMX 负责局部更新与 SSE 流式消费，Alpine.js 管理纯客户端状态，Tailwind CSS 负责样式。应用采用 hash 路由（`#/chat`、`#/knowledge` 等），完全无需修改后端路由策略。所有页面直接消费现有 `/api/*` 端点，并补充实现附件下载后端 API，以覆盖完整使用链路。

### Background & Research

Key findings from research phase:

- **Competitors:** 市场上缺乏可直接挂载到 FastAPI 的完整开源 RAG Web UI。Reflect Notes 的三栏布局、Capacities 的 AI 引用来源设计、Perplexity 的对话即研究工作流最值得借鉴。
- **UX/UI:** 推荐三栏式布局（导航 / 主内容 / 上下文侧栏），RAG 回答必须内嵌可点击来源引用；调研任务需要独立工作流页面，并通过 SSE 实时展示进度与决策节点。
- **Technical:** `src/web/static/` 和 `templates/` 已存在但为空；后端缺少附件下载 API（契约中有、代码中无）；SSE 流式聊天和调研进度推送已就绪；认证采用 Bearer JWT。

> Full research available in [research/README.md](../research/README.md)

---

## 2. Users & Personas

### Primary Persona

**Name:** 陈明 — 知识工作者
**Role:** 产品经理 / 独立研究者 / 自由撰稿人
**Context:** 每天需要收集和整理大量阅读材料、会议笔记、网页文章，并基于这些资料撰写报告或回答复杂问题。他重视隐私，倾向于将数据保存在本地而非云端 SaaS。
**Goals:**
- 快速把文本、文件、网页链接整理进个人知识库。
- 通过自然语言对话迅速找到已有资料中的答案。
- 针对陌生主题发起自动化调研，在短时间内获得结构化报告。
**Frustrations:**
- 现有工具要么过于复杂（Notion），要么 AI 能力碎片化（Obsidian 插件）。
- 不希望学习命令行或 REST API 才能使用自己的数据。

### Secondary Persona

**Name:** 刘薇 — 效率工具爱好者
**Role:** 技术人员 / 开源用户
**Context:** 熟悉在本地部署服务，愿意为隐私和自主可控牺牲一定的 polished 体验。她需要通过浏览器随时随地访问自己的知识助手。
**Goals:**
- 用浏览器完成所有操作，无需额外安装桌面客户端。
- 界面响应快、不臃肿，优先功能完整而非视觉花哨。

---

## 3. User Stories

### Must Have (MVP)

- [ ] **US-001 — 初始化与登录**
  As a user, I want to open the web app in my browser, set a password on first use, and log in with that password, so that my local data stays protected.
  **AC:**
  - 首次访问显示密码设置页（≥8 位，字母+数字）。
  - 后续访问显示登录页，支持"记住我"（7 天 JWT）。
  - Token 失效或服务重启后引导重新登录。

- [ ] **US-002 — Dashboard 概览**
  As a user, I want a landing dashboard that shows my knowledge count, LLM connection status, and quick entry points to chat/research/settings, so that I can orient myself immediately.
  **AC:**
  - 展示知识条目总数、最近 5 条知识、最近 3 个会话。
  - 展示系统状态（LLM/Embedding/Search 是否可用）。
  - 每个卡片/快捷入口可点击进入对应页面。

- [ ] **US-003 — 知识库浏览与搜索**
  As a user, I want to browse my knowledge items in a list, filter by tags, and search by keywords, so that I can quickly locate saved content.
  **AC:**
  - 列表支持分页（默认 20 条/页）。
  - 顶部有搜索框和标签筛选器。
  - 每条知识展示标题、摘要、标签、置信度等级、创建时间。
  - 支持软删除，删除后在列表中标记或隐藏（可切换"显示已删除"）。

- [ ] **US-004 — 添加与编辑知识**
  As a user, I want to add plain text, upload files, or submit URLs as knowledge entries, and edit existing ones, so that my knowledge base stays up to date.
  **AC:**
  - "新建"支持文本直接输入、文件上传（≤1GB）、URL 抓取。
  - 编辑时展示当前版本信息；内容修改超过 20% 触发新版本和置信度重评。
  - 附件提取失败时在 UI 明确提示错误原因。

- [ ] **US-005 — 查看知识详情与版本**
  As a user, I want to open a knowledge item to see its full content, tags, attachments, confidence score with rationale, and version history, so that I understand the provenance and reliability of the content.
  **AC:**
  - 详情页展示完整内容（Markdown 渲染）。
  - 标签可编辑；附件列表可下载（依赖新增下载 API）。
  - 置信度可视化展示（高/中/低）及评估依据。
  - 版本历史以时间线展示，可切换查看旧版本。

- [ ] **US-006 — 对话式查询与流式回答**
  As a user, I want to start or continue a conversation where I ask questions in natural language and receive streaming answers with citations, so that I can interactively explore my knowledge.
  **AC:**
  - 左侧边栏展示会话列表，支持新建/切换/重命名/删除。
  - 消息区域展示用户提问和 AI 回答；AI 回答以 SSE 流式逐字输出。
  - 回答中的引用必须可点击，悬浮或点击时展示来源知识摘要。
  - token 401 或 LLM 降级模式下给出明确提示。

- [ ] **US-007 — 提交与管理调研任务**
  As a user, I want to submit a research topic, watch real-time progress via SSE, and answer any decision prompts from the AI, so that I can get a structured research report without manual searching.
  **AC:**
  - 任务列表页展示所有调研任务的状态（queued/running/awaiting_input/completed/error）。
  - 新建任务需要输入主题和范围描述。
  - 任务详情页通过前端 `fetch + ReadableStream` 消费 SSE，展示进度和阶段性摘要。
  - `awaiting_input` 状态时暂停并展示选择/输入表单，用户提交后继续。

- [ ] **US-008 — 保存调研报告到知识库**
  As a user, I want to save a completed research report into my knowledge base with one click, so that it becomes searchable and quotable in future chats.
  **AC:**
  - 报告完成后展示"保存到知识库"按钮。
  - 保存成功后跳转至对应知识详情页或给出 Toast 提示。

- [ ] **US-009 — 系统设置**
  As a user, I want to configure LLM endpoints, embedding models, search APIs, privacy toggles, version retention, and perform export/import/reset from a settings page, so that I can control how my assistant behaves and back up my data.
  **AC:**
  - 设置页分组展示：LLM 配置、Embedding 配置、搜索 API、隐私策略、存储与日志、数据操作。
  - 隐私策略三个开关独立控制（发送完整知识 / 外部搜索 / 上传日志）。
  - 导出生成加密 ZIP 并触发浏览器下载；导入支持上传 ZIP 并展示汇总报告。
  - 重置操作需要二次密码确认。

### Should Have

- [ ] **US-010 — 移动端响应式适配**
  As a user, I want the web app to be usable on a tablet or phone, so that I can access my knowledge assistant from any device.
  **AC:**
  - 侧边栏在窄屏下变为顶部导航或抽屉。
  - 输入框、按钮的触摸目标 ≥44×44。
  - Chat 和 Research 页面在移动端保持核心功能可用。

- [ ] **US-011 — 知识库全局操作**
  As a user, I want to bulk-select knowledge items for bulk-tagging or bulk-deletion, so that I can manage large libraries efficiently.
  **AC:**
  - 列表支持多选复选框。
  - 选中后显示批量操作栏（批量加标签 / 批量删除）。

### Could Have (Future)

- [ ] **US-012 — 键盘快捷键**
  As a power user, I want keyboard shortcuts (e.g., `/` for search, `Cmd+K` for command palette) so that I can navigate faster.

- [ ] **US-013 — 深色模式主题切换**
  As a user, I want to toggle between light and dark themes so that the app is comfortable to use at night.

---

## 4. Feature Breakdown

### 4.1 Auth & Initialization

**Description:** 首次访问时的密码设置和后续登录逻辑。
**Key interactions:**
- 表单校验（密码长度、字母+数字）。
- 登录成功后存储 JWT（localStorage for "remember me", sessionStorage otherwise）。
- 拦截 401 响应，重定向到登录页并显示"会话已过期，请重新登录"。
**Edge cases:**
- 服务端重启导致 master key 缓存清空，旧 token 401 — 前端必须友好提示。
- 用户直接访问 `#/chat` 等页面但 token 不存在 — 重定向到 `#/login?redirect=chat`。

### 4.2 Dashboard

**Description:** 用户登录后的首页，提供系统概览和快捷入口。
**Key interactions:**
- 调用 `/api/system/status` 获取统计信息。
- 展示知识库、最近会话、活跃调研的快速入口卡片。
**Edge cases:**
- 首次使用无数据时展示 Empty State（"开始添加你的第一条知识"）。
- LLM 未配置或不可用时展示警告 Banner。

### 4.3 Knowledge Base (List + CRUD)

**Description:** 知识的浏览、搜索、筛选、添加、编辑、删除。
**Key interactions:**
- 列表：调用 `/api/knowledge?offset=&limit=&q=&tags=`。
- 新建文本：弹窗或跳转表单，调用 `POST /api/knowledge`。
- 上传文件：`<input type="file">` + `FormData` → `POST /api/knowledge/upload`。
- 添加 URL：表单提交 → `POST /api/knowledge/url`。
- 编辑：`PATCH /api/knowledge/{id}`。
- 删除：`DELETE /api/knowledge/{id}`（软删除）。
**Edge cases:**
- 上传大文件时展示进度（若浏览器支持 `XMLHttpRequest` progress）。
- 内容长度 < 5 字符时前端即时拦截并提示。
- 附件提取失败时显示 `extraction_status: failed` 和 `extraction_error`。

### 4.4 Knowledge Detail

**Description:** 单条知识的完整查看、版本历史、附件下载、置信度展示。
**Key interactions:**
- 详情：调用 `/api/knowledge/{id}`。
- 附件下载：调用新增 `GET /api/knowledge/{id}/attachments/{attachment_id}/download`。
- 手动触发置信度评估：`POST /api/knowledge/{id}/evaluate-confidence`。
- 版本时间线：展示 `versions` 数组，点击可切换查看旧版本内容。
**Edge cases:**
- 知识被软删除后仍能查看详情（用于历史引用）。
- 附件 MIME type 为图片时尝试浏览器内预览，其他类型触发下载。

### 4.5 Chat

**Description:** 自然语言对话，支持流式回答和来源引用。
**Key interactions:**
- 会话列表：调用 `/api/chat/conversations`。
- 加载历史消息：调用 `/api/chat/conversations/{id}/messages`。
- 发送消息：`POST /api/chat/conversations/{id}/messages`（带 `stream=true`，返回 SSE）。
- 前端使用 `fetch + ReadableStream` 手动解析 SSE，逐段渲染回答文本。
- 遇到 `citation` 事件时渲染可引用的来源 chip/link。
**Edge cases:**
- SSE 连接断开：前端自动重试（建议最多 3 次）。
- LLM 不可用时后端返回降级文案，前端展示警告 Banner。
- 新会话第一个消息默认调用 `POST /api/chat/conversations` 创建会话。

### 4.6 Research

**Description:** 提交调研任务、实时查看进度、回答 AI 决策、保存报告。
**Key interactions:**
- 任务列表：调用 `/api/research`。
- 新建任务：`POST /api/research`。
- 实时进度：`fetch` → `GET /api/research/{task_id}/events`，手动解析 SSE。
- `question` 事件暂停渲染，展示决策表单；提交后调用 `POST /api/research/{task_id}/respond`。
- 报告就绪后展示 Markdown 渲染的报告和"保存到知识库"按钮：`POST /api/research/{task_id}/save`。
**Edge cases:**
- `awaiting_input` 不设超时，前端持续展示等待表单直到用户操作。
- 服务端重启导致任务状态停滞在 `pending_recheck`，前端展示"外部服务恢复后将自动继续"。
- 任务并发超限（默认 2）时后端自动排队，前端通过列表页刷新查看状态。

### 4.7 Settings

**Description:** 系统配置、隐私策略、数据导入导出、系统重置。
**Key interactions:**
- 获取配置：`GET /api/system/config`。
- 更新配置：`PUT /api/system/config`。
- 导出：`POST /api/system/export` → 前端用 `Blob` + `URL.createObjectURL` 触发下载。
- 导入：`POST /api/system/import`（multipart ZIP）→ 展示结果汇总。
- 重置：`POST /api/system/reset`（带密码二次确认）。
**Edge cases:**
- 导入 ZIP 密码错误或格式损坏时展示后端返回的具体错误。
- 重置为危险操作，需弹窗要求输入当前密码确认。

---

## 5. Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-001 | 前端必须支持密码初始化页和登录页，密码校验规则与后端一致（≥8位，字母+数字）。 | Must | |
| FR-002 | Dashboard 必须展示系统状态（`llm_connected`、`embedding_available` 等）和快捷入口。 | Must | 调用 `/api/system/status` |
| FR-003 | 知识库列表必须支持关键词搜索、多标签过滤、分页。 | Must | |
| FR-004 | 知识库必须支持文本创建、文件上传（≤1GB）、URL 添加三种入库方式。 | Must | 文件上传使用 `FormData` |
| FR-005 | 知识详情页必须展示标签、附件列表、置信度、版本历史，并支持附件下载。 | Must | 依赖新增下载 API |
| FR-006 | Chat 页面必须展示会话历史侧边栏、消息流式渲染、内联来源引用。 | Must | SSE 使用 `fetch + ReadableStream` |
| FR-007 | Research 页面必须支持新建任务、SSE 进度展示、决策问答交互、报告保存。 | Must | |
| FR-008 | Settings 页面必须允许配置 LLM、Embedding、Search API、隐私策略、版本保留策略。 | Must | |
| FR-009 | Settings 必须支持导出/导入/重置操作，重置需二次确认。 | Must | |
| FR-010 | 路由必须采用 hash 路由（`#/page`），避免后端 catch-all 修改。 | Must | 零后端改动原则 |
| FR-011 | 前端所有状态变化（加载、错误、成功）必须有明确的视觉反馈（骨架屏、Toast、Inline error）。 | Must | UX 研究结论 |
| FR-012 | 前端应实现基础响应式布局，保证在 768px 以上和 768px 以下均可正常使用。 | Should | |
| FR-013 | 批量操作（多选标签/删除）应在知识库列表页提供。 | Should | |
| FR-014 | 键盘快捷键（如 `/` 聚焦搜索）可作为增强体验。 | Could | Future |

## 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | 页面首屏加载 ≤2s 在本地网络环境下；API 列表请求 TTFB ≤500ms。 |
| Accessibility | 遵循 WCAG 2.1 AA：焦点可见、表单有 label、按钮有 aria-label、AI 新消息使用 `aria-live="polite"`。 |
| Security | 不在前端持久化存储密码；JWT 存 `sessionStorage`（默认）或 `localStorage`（记住我）；导出/导入/重置需二次确认。 |
| Browser Compatibility | 支持 Chrome/Edge/Firefox/Safari 最新两个主版本；SSE fetch stream 需要现代浏览器（已排除 IE）。 |
| Maintainability | 代码按页面拆分（`pages/*.js`），API 封装集中在 `api.js`，样式使用 Tailwind 工具类而非手写 CSS。 |

## 7. Out of Scope (v1)

- 多语言国际化（i18n）。
- PWA / Service Worker / 离线缓存。
- 实时协作或多用户支持。
- 复杂的可视化图表（知识图谱、Graph View）。
- 端到端自动化 UI 测试（Playwright）—— 本次以功能实现和手工 QA 为主。

## 8. Success Criteria

- **SC-001:** 用户能够在 2 分钟内完成初始化并进入 Dashboard。
- **SC-002:** 90% 的对话查询能在 Web 界面中成功触发流式回答并获得可见的引用来源。
- **SC-003:** 用户能在不刷新页面的情况下完成完整的"提交调研主题 → 查看 SSE 进度 → 回答决策 → 保存报告到知识库"流程。
- **SC-004:** 设置页的所有配置变更能够在 500ms 内得到保存反馈。

详细量化指标参见 [metrics.md](./metrics.md)。

## 9. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| HTMX + fetch stream SSE 组合在边缘浏览器上出现兼容性问题 | Low | Medium | 限定浏览器兼容性范围； Edge/Chrome/Firefox/Safari 最新两版已完整支持 `ReadableStream` |
| 附件下载 API 延迟实现，导致文件型知识无法闭环 | Low | High | 在 Product Spec 中强制要求，并在 Plan/Tasks 中作为 Phase 6 的前置任务 |
| 单用户应用在移动端体验受限（屏幕小、输入复杂） | Medium | Low | 优先保证桌面可用；响应式作为 Should Have 在后续迭代完善 |
| 服务端重启后 token 401 造成用户困惑 | Medium | Medium | UI 统一拦截 401，展示"服务已重启，请重新登录"提示 |

## 10. Open Questions

1. 是否需要在 v1 中实现移动端底部导航栏，还是仅做基础的响应式折叠？
2. Chat 页面中的引用来源高亮是否需要精确到段落/句子级别，还是仅展示知识标题即可？
3. 知识库列表的默认排序是按时间倒序还是按相关性（当没有搜索词时）？

## 11. Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| 采用 hash 路由 | 零后端改动，与 FastAPI 现有 URL 结构无冲突 | 2026-04-10 |
| SSE token 通过前端 `fetch + ReadableStream` 传递 | 避免为 SSE 端点增加 query token 支持，保持后端稳定 | 2026-04-10 |
| 附件下载 API 必须在 Product Spec 阶段一并设计实现 | 否则文件型知识（图片/文档/音视频）无法闭环 | 2026-04-10 |
| 技术栈选 Jinja2 + HTMX + Alpine.js + Tailwind | 零 Node 依赖、SSE 原生支持好、后端团队友好 | 2026-04-10 |
| 不引入 Playwright 等 E2E 测试于 v1 | 功能补全优先，自动化 UI 测试纳入后续迭代 | 2026-04-10 |
