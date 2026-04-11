# Research Index: Web 前端页面开发

> Generated: 2026-04-10 | Feature: 003-web-frontend
> Input richness: 5/8 | Interview mode: PARTIAL
> Research dimensions: competitors, ux_patterns, codebase, tech_stack

## Executive Summary

为 PersonalKnowledgeAssistant 设计并开发一个挂载在 FastAPI 服务上的 Web 前端。后端 API 已完整覆盖知识库、对话、调研、系统设置等能力，当前缺少用户界面。研究确定了**Jinja2 + HTMX + Alpine.js + Tailwind CSS** 作为最优技术方案，并识别出后端需补充附件下载端点这一关键缺口。

## Key Findings

| Dimension | Top Insight |
|-----------|-------------|
| 🏆 Competitors | Reflect Notes、Capacities、Perplexity 的 AI Chat + 知识库融合设计最具参考价值；市场上缺乏可直接挂载到 FastAPI 的完整开源替代方案 |
| 🎨 UX/UI | 推荐采用三栏式布局（导航 / 主内容 / 上下文侧栏），RAG 回答必须内嵌可点击来源引用；调研任务需要独立工作流页面 |
| 🔧 Codebase | `src/web/static/` 和 `templates/` 已存在但为空；后端缺少附件下载 API；现有认证使用 Bearer JWT；SSE 流式聊天和调研进度已就绪 |
| 🔒 Constraints | 单用户固定 id=1；服务重启后 master key 缓存丢失导致旧 token 401；调研任务 `awaiting_input` 无超时 |
| 📦 Tech Stack | Jinja2 + HTMX + Alpine.js 为最佳组合：零 Node 依赖、SSE 原生支持好、与 FastAPI 集成度最高 |
| 📊 Metrics | Skipped — MVP 功能补全阶段，暂不进行 ROI 量化研究 |

## Research Documents

| Document | Status | Key Insight |
|----------|--------|-------------|
| [competitors.md](./competitors.md) | ✅ | Reflect / Capacities / Perplexity 为 Top 3 参考；本地化+自部署的完整 RAG Web UI 是市场空白 |
| [ux-patterns.md](./ux-patterns.md) | ✅ | Co-Pilot 对话协同、透明化思考状态、渐进式披露为核心模式；移动端需 Bottom Input Bar + 抽屉式侧边栏 |
| [codebase-analysis.md](./codebase-analysis.md) | ✅ | 最小侵入式集成可行；必须补充附件下载与 SSE token 传递策略决策 |
| [tech-stack.md](./tech-stack.md) | ✅ | 推荐 HTMX 2.0.8 + Alpine.js 3.x + Tailwind v4； prioritizes 部署极简与后端团队友好 |

## Synthesis: Recommended Approach

1. **前端形态**：在 `src/web/static/` 中构建以 Jinja2 为页面骨架、HTMX 负责局部更新和 SSE 流式响应的轻量 Web 应用，Alpine.js 处理纯客户端状态（模态框、Tab 切换）。样式使用 Tailwind CSS（开发期 Play CDN，生产期预编译为单一 CSS 文件）。
2. **页面结构**：Login/Init → Dashboard → Knowledge Base（列表/搜索/标签/CRUD/上传）→ Chat（会话侧边栏 + 流式消息 + 引用高亮）→ Research（任务列表 + SSE 进度 + 决策弹窗）→ Settings（配置表单 + 导出/导入）。
3. **关键后端补充**：`GET /api/knowledge/{item_id}/attachments/{attachment_id}/download` 必须实现，否则文件型知识无法完整支持。
4. **认证与 SSE**：登录后持久化 JWT；SSE 推荐前端使用 `fetch + ReadableStream` 手动解析以携带 Bearer Header，避免修改后端；若采用原生 EventSource 则需后端增加 query token 支持。

## Open Questions for Product Spec

1. 路由策略：hash 路由（零后端改动）还是 history 路由（需 catch-all）？
2. SSE token 传递：前端 fetch stream 手动解析，还是后端为 SSE 增加 `?token=` 支持？
3. 是否需要在 Product Spec 阶段一并设计后端附件下载 API？
4. 是否要求兼容到特定浏览器版本？
5. 是否需要为前端编写 Playwright 等自动化 UI 测试？

## Red Flags / Risks Identified

- **后端能力缺口**：当前代码库中缺少附件下载路由，若 Spec 不覆盖，前端无法实现完整的文件知识管理。
- **SSE 断线恢复**：Research Worker 和 SSE Queue 均为内存实现，服务端重启后客户端需要重新连接并可能丢失进度上下文。
- **Token 失效陷阱**：服务端重启清掉 master key 缓存，旧 JWT（即使未过期）也会 401，用户会被迫重新登录，需要在 UI 中明确提示。
