# Metrics & Success Criteria: 003-web-frontend

> Feature: 003-web-frontend | Related: [Product Spec](./product-spec.md)

---

## Success Definition

在 v1 发布后的 30 天内，用户能够通过 Web 界面独立完成从初始化到使用核心功能（知识入库、对话查询、调研任务）的完整链路，而无需依赖命令行或第三方 API 客户端。Web 前端成为用户使用 PersonalKnowledgeAssistant 的默认入口。

---

## KPIs

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| 首次使用到发送第一条 Chat 消息的时间 | N/A（无 UI 时不可用） | ≤3 分钟 | 手工 QA + 屏幕录制计时 |
| Chat 流式回答成功率 | N/A | ≥90% | QA 测试：10 次提问中 9 次以上成功获得流式回答和引用 |
| 端到端调研任务完成率 | N/A | 100%（测试环境） | QA 测试：提交主题 → 查看进度 → 回答决策 → 保存报告 |
| 页面首屏加载时间（本地） | N/A | ≤2 秒 | Lighthouse / 浏览器 DevTools |
| 设置配置保存反馈延迟 | N/A | ≤500ms | DevTools Network 面板测量 API 响应时间 |

---

## Leading Indicators

| Indicator | Why it matters | Target |
|-----------|---------------|--------|
| 各页面无阻塞性报错 | 说明前端与后端 API 集成正常 | 0 P0/P1 UI 阻塞 bug |
| SSE 连接稳定性 | Chat 和 Research 的核心体验依赖 SSE | 连续 5 分钟对话无断流 |
| 附件下载 API 可用性 | 文件型知识的闭环关键 | 下载成功率 100%（测试环境） |

---

## Guardrail Metrics

以下指标在实施 Web 前端时**不得退化**：

| Guardrail | Threshold | How to monitor |
|-----------|-----------|----------------|
| FastAPI 服务启动时间 | 增加 <2 秒（静态文件挂载开销） | 本地 `time uvicorn src.main:app` 对比 |
| `/api/system/status` P95 响应时间 | 保持 &lt; 200ms | DevTools / 集成测试断言 |
| 二进制包/部署体积增长 | 增加 < 5MB（纯静态资源） | `du -sh src/web/static/` |

---

## Measurement Plan

- **Day 1 (开发完成):** 手工走通 Login → Dashboard → Knowledge → Chat → Research → Settings 全链路，记录首次遇到问题。
- **Week 1 (集成测试):** 运行 QA 测试集（由 001-ai-knowledge-assistant 的 `qa/extended_qa_tests.py` 扩展而来），验证 API + UI 集成是否通过。
- **Day 30 (使用反馈):** 若可能，收集用户是否把 Web 界面作为主要入口的主观反馈。

---

## Anti-metrics (what failure looks like)

- 用户仍然主要使用 curl 或 API 文档来操作系统。
- Chat 页面流式输出频繁中断或无法展示引用来源。
- 文件上传后无法在前端下载或预览附件。
- 移动端完全不可用，导致用户无法在平板等设备上访问。
