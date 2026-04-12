# Spec: Web 前端页面开发

> **Product Forge Feature** | Generated: 2026-04-10
> Feature slug: `003-web-frontend` | SpecKit mode: classic
>
> **Source artifacts:**
> - Product Spec: [product-spec/README.md](./product-spec/README.md)
> - Research: [research/README.md](./research/README.md)

---

## Overview

### What We're Building

为 PersonalKnowledgeAssistant 的现有 FastAPI 服务挂载一个零 Node 依赖的轻量 Web 前端。前端采用 Jinja2 模板为页面骨架，HTMX 负责局部更新与 SSE 流式消费，Alpine.js 管理纯客户端状态，Tailwind CSS 负责样式。应用通过 hash 路由（`#/login`、`#/dashboard`、`#/knowledge`、`#/chat`、`#/research`、`#/settings`）实现完全的前后端解耦，并补充实现附件下载后端 API，覆盖完整使用链路。

### Why We're Building It

当前 `001-ai-knowledge-assistant` 后端已完整实现知识库管理、对话式 RAG 查询、异步调研、系统设置等全部能力，但服务仅暴露 REST API 和 Swagger 文档。非技术用户无法直接使用，导致文件上传、导出/导入、会话浏览、流式聊天等核心体验完全缺失。Web 前端是将后端能力转化为可用产品的必经桥梁。

### Research Backing

This spec is backed by a full research phase covering:

- **Competitor analysis:** 市场上缺乏可直接挂载到 FastAPI 的完整开源 RAG Web UI。Reflect Notes（三栏布局）、Capacities（AI 引用来源）、Perplexity（对话即研究）是最值得借鉴的竞品。
- **UX/UI patterns:** 推荐三栏式布局（导航 / 主内容 / 上下文侧栏），RAG 回答必须内嵌可点击来源引用；调研任务需要独立工作流页面，并通过 SSE 实时展示进度与决策节点。
- **Codebase analysis:** `src/web/static/` 和 `templates/` 已存在但为空；后端缺少附件下载 API；SSE 流式聊天和调研进度推送已就绪；认证采用 Bearer JWT。

> Deep-dive: [research/README.md](./research/README.md)

---

## Prerequisites

| Priority | Feature | Status | Relationship | What's Needed |
|----------|---------|--------|--------------|---------------|
| P1 | 001-ai-knowledge-assistant | ✅ done | blocks | 后端 API（知识库、Chat、Research、System、Auth）必须已完成并稳定 |

---

## Goals

### Primary Goal

用户能够在浏览器中独立完成初始化、知识入库、对话查询、调研任务、系统设置的全部操作，无需命令行或第三方 HTTP 客户端。

### Secondary Goals

1. 通过 Web 界面完整消费后端 SSE 能力（Chat 流式回答、Research 实时进度）。
2. 保持部署极简：零 Node.js 运行时依赖，静态资源随 Python 服务一次启动即可运行。
3. 建立前后端解耦的 hash 路由方案，避免修改 FastAPI 现有 URL 结构。

### Non-Goals (v1 scope)

- 多语言国际化（i18n）。
- PWA / Service Worker / 离线缓存。
- 实时协作或多用户支持。
- 知识图谱可视化（Graph View）。
- 端到端自动化 UI 测试（Playwright）—— 以手工 QA 为主。

---

## Users

### Primary Persona

**陈明** — 知识工作者（产品经理 / 独立研究者 / 自由撰稿人）
Key need: 通过浏览器快速整理资料、对话查询已有知识、针对陌生主题发起自动化调研。

### Secondary Personas

**刘薇** — 效率工具爱好者 / 开源用户
Key need: 本地部署、隐私可控、浏览器即可访问，界面简洁不臃肿。

---

## User Stories

> Full user journey flows: [product-spec/user-journey.md](./product-spec/user-journey.md)

### Must Have (MVP)

- [x] **US-001 — 初始化与登录**
  As a user, I want to open the web app in my browser, set a password on first use, and log in with that password, so that my local data stays protected.
  - **AC:**
    - 首次访问显示密码设置页（≥8 位，字母+数字）。
    - 后续访问显示登录页，支持"记住我"（7 天 JWT）。
    - Token 失效或服务重启后引导重新登录。
  - **Wireframe ref:** [Login](./product-spec/wireframes/wireframe-login.html)

- [x] **US-002 — Dashboard 概览**
  As a user, I want a landing dashboard that shows my knowledge count, LLM connection status, and quick entry points to chat/research/settings, so that I can orient myself immediately.
  - **AC:**
    - 展示知识条目总数、最近 5 条知识、最近 3 个会话。
    - 展示系统状态（LLM/Embedding/Search 是否可用）。
    - 每个卡片/快捷入口可点击进入对应页面。
  - **Wireframe ref:** [Dashboard](./product-spec/wireframes/wireframe-dashboard.html)

- [x] **US-003 — 知识库浏览与搜索**
  As a user, I want to browse my knowledge items in a list, filter by tags, and search by keywords, so that I can quickly locate saved content.
  - **AC:**
    - 列表支持分页（默认 20 条/页）。
    - 顶部有搜索框和标签筛选器。
    - 每条知识展示标题、摘要、标签、置信度等级、创建时间。
  - **Wireframe ref:** [Knowledge List](./product-spec/wireframes/wireframe-knowledge-list.html)

- [x] **US-004 — 添加与编辑知识**
  As a user, I want to add plain text, upload files, or submit URLs as knowledge entries, and edit existing ones, so that my knowledge base stays up to date.
  - **AC:**
    - "新建"支持文本直接输入、文件上传（≤1GB）、URL 抓取。
    - 编辑时展示当前版本信息；内容修改超过 20% 触发新版本和置信度重评。
    - 附件提取失败时在 UI 明确提示错误原因。
  - **Wireframe ref:** [Knowledge Detail](./product-spec/wireframes/wireframe-knowledge-detail.html)

- [x] **US-005 — 查看知识详情与版本**
  As a user, I want to open a knowledge item to see its full content, tags, attachments, confidence score with rationale, and version history, so that I understand the provenance and reliability of the content.
  - **AC:**
    - 详情页展示完整内容（Markdown 渲染）。
    - 标签可编辑；附件列表可下载（依赖新增下载 API）。
    - 置信度可视化展示（高/中/低）及评估依据。
    - 版本历史以时间线展示，可切换查看旧版本。
  - **Wireframe ref:** [Knowledge Detail](./product-spec/wireframes/wireframe-knowledge-detail.html)

- [x] **US-006 — 对话式查询与流式回答**
  As a user, I want to start or continue a conversation where I ask questions in natural language and receive streaming answers with citations, so that I can interactively explore my knowledge.
  - **AC:**
    - 左侧边栏展示会话列表，支持新建/切换/重命名/删除。
    - 消息区域展示用户提问和 AI 回答；AI 回答以 SSE 流式逐字输出。
    - 回答中的引用必须可点击，悬浮或点击时展示来源知识摘要。
  - **Wireframe ref:** [Chat](./product-spec/wireframes/wireframe-chat.html)

- [x] **US-007 — 提交与管理调研任务**
  As a user, I want to submit a research topic, watch real-time progress via SSE, and answer any decision prompts from the AI, so that I can get a structured research report without manual searching.
  - **AC:**
    - 任务列表页展示所有调研任务的状态（queued/running/awaiting_input/completed/error）。
    - 新建任务需要输入主题和范围描述。
    - 任务详情页通过前端 `fetch + ReadableStream` 消费 SSE，展示进度和阶段性摘要。
    - `awaiting_input` 状态时暂停并展示选择/输入表单，用户提交后继续。
  - **Wireframe ref:** [Research List](./product-spec/wireframes/wireframe-research-list.html) · [Research Detail](./product-spec/wireframes/wireframe-research-detail.html)

- [x] **US-008 — 保存调研报告到知识库**
  As a user, I want to save a completed research report into my knowledge base with one click, so that it becomes searchable and quotable in future chats.
  - **AC:**
    - 报告完成后展示"保存到知识库"按钮。
    - 保存成功后 Toast 提示，可跳转至对应知识详情页。

- [x] **US-009 — 系统设置**
  As a user, I want to configure LLM endpoints, embedding models, search APIs, privacy toggles, version retention, and perform export/import/reset from a settings page, so that I can control how my assistant behaves and back up my data.
  - **AC:**
    - 设置页分组展示：LLM 配置、Embedding 配置、搜索 API、隐私策略、存储与日志、数据操作。
    - 隐私策略三个开关独立控制（发送完整知识 / 外部搜索 / 上传日志）。
    - 导出生成加密 ZIP 并触发浏览器下载；导入支持上传 ZIP 并展示汇总报告。
    - 重置操作需要二次密码确认。
  - **Wireframe ref:** [Settings](./product-spec/wireframes/wireframe-settings.html)

### Should Have

- [x] **US-010 — 移动端响应式适配**
  As a user, I want the web app to be usable on a tablet or phone, so that I can access my knowledge assistant from any device.
  - **AC:** 侧边栏在窄屏下变为顶部导航或抽屉；输入框、按钮的触摸目标 ≥44×44。

- [ ] **US-011 — 知识库全局操作**
  As a user, I want to bulk-select knowledge items for bulk-tagging or bulk-deletion, so that I can manage large libraries efficiently.

### Could Have (Future)

- [ ] **US-012 — 键盘快捷键**
  As a power user, I want keyboard shortcuts (e.g., `/` for search, `Cmd+K` for command palette).

- [ ] **US-013 — 深色模式主题切换**
  As a user, I want to toggle between light and dark themes.

---

## Functional Requirements

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-001 | 前端必须支持密码初始化页和登录页，密码校验规则与后端一致（≥8位，字母+数字）。 | Must | US-001 |
| FR-002 | Dashboard 必须展示系统状态（llm_connected、embedding_available 等）和快捷入口。 | Must | US-002 |
| FR-003 | 知识库列表必须支持关键词搜索、多标签过滤、分页。 | Must | US-003 |
| FR-004 | 知识库必须支持文本创建、文件上传（≤1GB）、URL 添加三种入库方式。 | Must | US-004 |
| FR-005 | 知识详情页必须展示标签、附件列表、置信度、版本历史，并支持附件下载。 | Must | US-005 |
| FR-006 | Chat 页面必须展示会话历史侧边栏、消息流式渲染、内联来源引用。 | Must | US-006 |
| FR-007 | Research 页面必须支持新建任务、SSE 进度展示、决策问答交互、报告保存。 | Must | US-007 |
| FR-008 | Settings 页面必须允许配置 LLM、Embedding、Search API、隐私策略、版本保留策略。 | Must | US-009 |
| FR-009 | Settings 必须支持导出/导入/重置操作，重置需二次确认。 | Must | US-009 |
| FR-010 | 路由必须采用 hash 路由（#/page），避免后端 catch-all 修改。 | Must | 架构决策 |
| FR-011 | 前端所有状态变化（加载、错误、成功）必须有明确的视觉反馈。 | Must | UX 研究 |
| FR-012 | 前端应实现基础响应式布局，保证在 768px 以上和 768px 以下均可正常使用。 | Should | US-010 |
| FR-013 | 后端必须补充 `GET /api/knowledge/{id}/attachments/{attachment_id}/download` 端点。 | Must | US-005 |

---

## Non-Functional Requirements

| Category | Requirement | Source |
|----------|-------------|--------|
| Performance | 页面首屏加载 ≤2s（本地网络）；API 列表请求 TTFB ≤500ms。 | product-spec |
| Accessibility | 遵循 WCAG 2.1 AA：焦点可见、表单有 label、按钮有 aria-label、AI 新消息使用 `aria-live="polite"`。 | research/ux-patterns |
| Security | 不在前端持久化存储密码；JWT 默认存 `sessionStorage`；危险操作需二次确认。 | product-spec |
| Browser Compatibility | 支持 Chrome/Edge/Firefox/Safari 最新两个主版本；SSE fetch stream 需要现代浏览器。 | product-spec |
| Maintainability | 代码按页面拆分（`pages/*.js`），API 封装集中在 `api.js`，样式使用 Tailwind 工具类。 | product-spec |

## NFR Measurement Contract

| NFR | How to Measure | Signal / Query | Threshold |
|-----|----------------|----------------|-----------|
| 首屏加载时间 | Lighthouse Performance / DevTools Network | `DOMContentLoaded` 事件 ≤2s | ≤2s |
| API 列表 TTFB | DevTools Network 面板测量 `GET /api/knowledge` | Network tab Timing `Waiting for server response` | ≤500ms |
| 焦点可见性 | 手动键盘 Tab 遍历所有交互元素 | 每个可聚焦元素均有 ≥2px 可见焦点环 | 100% 通过 |
| Chat SSE 稳定性 | QA 测试中连续发起 10 轮对话 | 流式输出无异常中断 | ≥90% 成功率 |

---

## Technical Context

> Detailed analysis: [research/codebase-analysis.md](./research/codebase-analysis.md)

### Integration Points

| Layer | Location | Change Type | Description |
|-------|----------|-------------|-------------|
| FastAPI StaticFiles | `src/main.py` | Extend | 静态文件挂载 `/static` 已存在，补充 `index.html` 和前端资源 |
| Jinja2 Templates | `src/web/templates/` | New | 页面骨架使用 Jinja2 渲染，HTMX 负责局部更新 |
| Auth Middleware | `src/auth/dependencies.py` | Reuse | 现有 Bearer JWT 校验，前端负责携带 token |
| Knowledge API | `src/knowledge/router.py` | Extend | 新增附件下载路由 `GET /api/knowledge/{id}/attachments/{attachment_id}/download` |
| Chat API | `src/chat/router.py` | Reuse | SSE 流式响应已就绪，前端用 fetch stream 消费 |
| Research API | `src/research/router.py` | Reuse | SSE 进度推送已就绪 |
| System API | `src/system/router.py` | Reuse | 配置、导出、导入、重置端点直接复用 |

### Reusable Components

| Component/Service | Location | How to Reuse |
|------------------|----------|--------------|
| StaticFiles mount | `src/main.py` | 已配置 `/static`，直接放入前端资源 |
| JWT auth | `src/auth/router.py` | 前端调用 `/api/auth/login` 获取 token |
| Knowledge CRUD | `src/knowledge/router.py` | 直接消费现有 REST API |
| Chat SSE | `src/chat/router.py` | `POST /api/chat/conversations/{id}/messages?stream=true` |
| Research SSE | `src/research/router.py` | `GET /api/research/{task_id}/events` |

### New Modules Required

1. **前端资源目录** `src/web/static/`
   - `index.html` — SPA 入口
   - `css/app.css` — Tailwind 预编译样式
   - `js/api.js` — 统一 API 封装
   - `js/router.js` — hash 路由管理
   - `js/sse.js` — `fetch + ReadableStream` SSE 解析器
   - `js/pages/*.js` — 各页面逻辑
2. **后端附件下载路由** `src/knowledge/router.py`
   - `GET /api/knowledge/{item_id}/attachments/{attachment_id}/download`
   - 使用 `get_cached_master_key` 解密文件并返回 `StreamingResponse`

### Data Model Impact

- 前端为展示层，**不引入新的数据库表**。
- 后端新增下载路由依赖现有 `attachments` 表字段：`storage_path`、`mime_type`、`filename`。

### Tech Stack Notes

- **HTMX 2.0.8** — 局部 AJAX 更新、SSE 扩展支持（用于非鉴权场景或配合 query token 的场景）。本项目中 Chat/Research SSE 因 Bearer Header 需求，主要采用 `fetch + ReadableStream` 方案。
- **Alpine.js 3.x** — 模态框展开/收起、Tab 切换、表单即时校验等纯客户端状态管理。
- **Tailwind CSS v4** — 开发阶段使用 Play CDN 快速迭代，生产阶段通过 Tailwind CLI 预编译为单一 CSS 文件提交到仓库。

### Codebase Constraints

> From `research/codebase-analysis.md` — constraints the architecture must respect.

| Constraint | Source | Impact |
|------------|--------|--------|
| 单用户固定 id=1 | `src/auth/dependencies.py` / system models | 前端不应出现多用户管理概念 |
| 服务端重启后 master key 缓存丢失 | `src/auth/service.py` | 旧 token 会 401，前端必须全局拦截并友好提示重新登录 |
| 密码规则 ≥8 位且含字母+数字 | `src/system/router.py` | 前端表单校验必须与后端一致 |
| 调研任务 `awaiting_input` 不设超时 | `spec.md` (001) | 前端需持续展示等待表单直到用户操作 |
| file storage 路径为 `files/AB/CD/<item-id>/` | `src/knowledge/service.py` | 前端不直接访问文件系统，所有文件操作走 API |

---

## Acceptance Criteria

Each user story's AC is listed above. Additionally, the feature is considered complete when:

1. All Must Have user stories are implemented and backend download API is verified.
2. All wireframes match the implemented UI within acceptable deviation.
3. Performance NFRs are met (measured by DevTools / Lighthouse).
4. Accessibility requirements pass manual keyboard navigation and screen-reader spot-check.
5. Hash routing works across all 6 main views without backend 404 on refresh.

---

## Success Metrics

> Full metrics definition: [product-spec/metrics.md](./product-spec/metrics.md)

Primary KPI: 首次使用到发送第一条 Chat 消息的时间 — Target: ≤3 分钟 (Baseline: N/A)

---

## Testing Specification

### Coverage Targets

| Module / Service | Target Coverage | Test Type |
|-----------------|----------------|-----------|
| 新增附件下载 API | ≥ 80% | integration |
| 前端手工 QA | 100% 核心链路 | manual / e2e |

### Critical Test Cases

| # | Scenario | Input | Expected Output | Type |
|---|----------|-------|----------------|------|
| TC-001 | 用户登录后浏览 Dashboard | 有效密码 | Dashboard 展示系统状态和快捷入口 | manual |
| TC-002 | 上传文件并下载附件 | PDF 文件 ≤1GB | 上传成功，详情页可点击下载原始文件 | integration |
| TC-003 | Chat 流式回答带引用 | 已存在知识的问题 | SSE 返回完整回答，内嵌可点击引用 | manual |
| TC-004 | 调研任务决策问答 | 提交宽泛主题 | SSE 推送问题事件，用户回答后继续生成报告 | manual |
| TC-005 | 服务端重启后 token 401 | 已登录状态下重启服务 | 前端拦截 401 并引导重新登录 | manual |
| TC-006 | 设置页导出备份 | 点击导出按钮 | 浏览器触发 ZIP 下载 | integration |

### E2E Scenarios

| TC-ID | Scenario | Entry Point | Exit Condition |
|-------|----------|------------|----------------|
| TC-E2E-001 | 完整首次使用链路 | 浏览器访问 `/`（未初始化） | 初始化 → 登录 → 添加知识 → Chat 提问 → 获得带引用的回答 |
| TC-E2E-002 | 调研任务完整生命周期 | 登录后进入 Research | 提交主题 → SSE 进度正常 → 回答决策 → 保存报告到知识库 → 报告中知识可在 Chat 被引用 |
| TC-E2E-003 | 服务重启后的恢复体验 | 登录后重启后端 | 前端下一次请求触发 401 → 友好提示 → 重新登录 → 恢复之前会话 |

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| fetch stream SSE 在边缘浏览器兼容性问题 | Medium | 限定支持 Chrome/Edge/Firefox/Safari 最新两版；这些浏览器均已完整支持 ReadableStream |
| 附件下载 API 延迟实现导致文件型知识无法闭环 | High | 在 spec 中强制要求，在 Plan/Tasks 中作为前置任务 |
| 服务端重启后 token 401 造成用户困惑 | Medium | UI 统一拦截 401，展示"服务已重启，请重新登录"提示 |
| HTMX + fetch stream 组合增加前端调试复杂度 | Low | 按页面拆分代码，`sse.js` 集中封装，保持接口一致 |

---

## Wireframes Reference

> Visual wireframes: [product-spec/wireframes/](./product-spec/wireframes/)

Key screens:
- [Login](./product-spec/wireframes/wireframe-login.html) — 密码设置与登录
- [Dashboard](./product-spec/wireframes/wireframe-dashboard.html) — 系统概览与快捷入口
- [Knowledge List](./product-spec/wireframes/wireframe-knowledge-list.html) — 知识浏览、搜索、筛选
- [Knowledge Detail](./product-spec/wireframes/wireframe-knowledge-detail.html) — 知识内容、版本、附件、置信度
- [Chat](./product-spec/wireframes/wireframe-chat.html) — 会话列表与流式对话
- [Research List](./product-spec/wireframes/wireframe-research-list.html) — 调研任务管理
- [Research Detail](./product-spec/wireframes/wireframe-research-detail.html) — SSE 进度与决策交互
- [Settings](./product-spec/wireframes/wireframe-settings.html) — 配置与数据操作

---

## Open Questions

1. Chat 页面中的引用来源高亮是否需要精确到段落/句子级别，还是仅展示知识标题即可？（v1 建议仅展示标题和摘要）
2. 知识库列表的默认排序是按时间倒序还是按相关性（当没有搜索词时）？（建议：时间倒序）
3. 移动端底部导航栏是否在 v1 中实现，还是仅做侧边栏/顶栏的折叠适配？（建议：折叠适配优先）
