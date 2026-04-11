# Product Spec Index: Web 前端页面开发

> Status: DRAFT | Created: 2026-04-10 | Last updated: 2026-04-10
> Feature slug: `003-web-frontend`
> ← [Back to Feature Root](../README.md) | ← [Research](../research/README.md)

## What We're Building

为 PersonalKnowledgeAssistant 的现有 FastAPI 服务挂载一个零 Node 依赖的轻量 Web 前端。前端采用 Jinja2 + HTMX + Alpine.js + Tailwind CSS 技术栈，通过 hash 路由实现登录、Dashboard、知识库管理、对话式查询、调研任务跟踪、系统设置等全部页面，完整消费后端已有的 `/api/*` 端点。

## Document Map

| Document | Purpose | Detail Level | Status |
|----------|---------|--------------|--------|
| [product-spec.md](./product-spec.md) | 主 PRD — 目标、用户故事、功能/非功能需求、风险 | Exhaustive | DRAFT |
| [user-journey.md](./user-journey.md) | 从初始化到保存调研报告的完整用户旅程 | Standard | DRAFT |
| [wireframes/](./wireframes/) | 8 个页面的详细 HTML 线框图 | Detailed HTML | DRAFT |
| [metrics.md](./metrics.md) | KPI 和成功标准 | Detailed | DRAFT |
| [mockups/](./mockups/) | 通用风格的交互式高保真 mockups（含导航页） | Generic | DRAFT |

## Wireframes

- [wireframe-login.html](./wireframes/wireframe-login.html)
- [wireframe-dashboard.html](./wireframes/wireframe-dashboard.html)
- [wireframe-knowledge-list.html](./wireframes/wireframe-knowledge-list.html)
- [wireframe-knowledge-detail.html](./wireframes/wireframe-knowledge-detail.html)
- [wireframe-chat.html](./wireframes/wireframe-chat.html)
- [wireframe-research-list.html](./wireframes/wireframe-research-list.html)
- [wireframe-research-detail.html](./wireframes/wireframe-research-detail.html)
- [wireframe-settings.html](./wireframes/wireframe-settings.html)

## Mockups

- [mockups/index.html](./mockups/index.html) — 导航页
- [mockup-login.html](./mockups/mockup-login.html)
- [mockup-dashboard.html](./mockups/mockup-dashboard.html)
- [mockup-knowledge-list.html](./mockups/mockup-knowledge-list.html)
- [mockup-knowledge-detail.html](./mockups/mockup-knowledge-detail.html)
- [mockup-chat.html](./mockups/mockup-chat.html)
- [mockup-research-list.html](./mockups/mockup-research-list.html)
- [mockup-research-detail.html](./mockups/mockup-research-detail.html)
- [mockup-settings.html](./mockups/mockup-settings.html)

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 路由策略 | hash 路由 | 零后端改动 |
| SSE token 传递 | 前端 `fetch + ReadableStream` | 不改后端 SSE 端点 |
| 技术栈 | Jinja2 + HTMX + Alpine.js + Tailwind | 零 Node 依赖、后端团队友好 |
| 附件下载 API | 强制在 v1 实现 | 否则文件型知识无法闭环 |

## Must Read

> 建议阅读顺序：
> 1. [product-spec.md](./product-spec.md) — 了解完整需求
> 2. [user-journey.md](./user-journey.md) — 理解用户完整流程
> 3. [wireframes/](./wireframes/) — 查看页面结构和灰度线框
> 4. [mockups/](./mockups/) — 浏览高保真视觉参考
