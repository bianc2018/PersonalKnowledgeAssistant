# Changelog

## [Web 前端页面开发] - 2026-04-11

### Added
- 为 `001-ai-knowledge-assistant` 后端挂载完整的零 Node 依赖 Web 前端
- 新增页面模块：Login / Init、Dashboard、Knowledge（列表/详情/创建/编辑）、Chat、Research、Settings
- 实现附件下载 API `GET /api/knowledge/{id}/attachments/{attachment_id}/download`，支持 AES-256-GCM 解密流式返回
- 实现基于 `fetch + ReadableStream` 的 SSE 解析器（`sse.js`），支持 Chat 流式回答与 Research 实时进度推送
- 实现 hash 路由（`router.js`）、Bearer JWT 认证拦截（`api.js`）、全局 Toast / Modal / Skeleton UI 组件
- 响应式布局适配（侧边栏折叠、触摸目标 ≥44px）、手动无障碍检查（焦点环、aria-live、键盘导航）

### Changed
- `deploy.py` Python 版本要求从 `>= 3.11` 调整为 `>= 3.10`，匹配 CI 环境

### Fixed
- **P0** 修复 Chat SSE 完全失效：`sse.js` 未支持 POST 方法与 `event:` 字段；`chat.js` 错误地双重调用 `apiPost` 与 `createSSEStream`
- **P1** 修复 `renderMarkdown` 中 `marked.parse` 的废弃 `sanitize` 选项导致的 XSS 风险
- **P1** 在 `knowledge.js`、`research.js`、`dashboard.js` 中对所有模板字符串动态插值增加 `escapeHtml`
- **P2** 修复 `router.js` 未 `await` 异步页面渲染，导致异常被静默吞没
- 修复 `test_deploy_e2e.py` 因完整 `requirements.txt` 导致 `pip install` 超时的问题

### Technical Notes
- 前端技术栈：Jinja2 Shell + HTMX 2.0.8 + Alpine.js 3.x + Tailwind CSS v4 (Play CDN) + marked.js
- 后端测试：pytest 31/31 全部通过（包含附件下载集成测试与部署脚本测试）
- 所有 Must Have 用户故事（US-001~US-009）与 Should Have 响应式适配（US-010）均已实现并验证

## [AI 知识管理助手] - 2026-04-07

### Added
- 补充 `001-ai-knowledge-assistant` 完整 QA 自动化测试报告（`qa-2026-04-07.md`）
- 添加扩展 QA 测试脚本 `extended_qa_tests.py`，覆盖 22 个 API 层测试场景
- 添加测试响应快照（`responses/`），为知识管理、对话查询、调研任务、置信度评估提供可复现证据

### Changed
- 无

### Fixed
- 无

### Technical Notes
- 核心功能实现代码已在此前合并至 main；本条目对应 QA 测试 artifacts 的补充提交
- 14 项集成测试全部通过，11 项扩展 QA 测试通过、1 项跳过（ASGI transport SSE 流读取限制）
- 因测试环境未配置外部 LLM，RAG 引用准确性、调研报告质量、置信度评分等 LLM 依赖场景需在配置真实端点后补充验证

## [Retrospective & Constitution Update] - 2026-04-07

### Added
- 生成 `002-one-click-deployment` 的 retrospective 报告，记录功能周期指标、spec 准确率、plan 有效性、实现质量
- 在项目章程 `constitution.md` 中新增两条原则：
  - 契约优先于实现 (Contract Over Code)
  - 系统级探测需要双重验证 (Verify System Assertions Twice)
- 安装 speckit retro 扩展及配套技能定义

### Changed
- 项目章程版本从 1.0.0 更新至 1.1.0

### Fixed
- 无

### Technical Notes
- retrospective 报告位于 `specs/002-one-click-deployment/retros/retro-20260407.md`
- 两条新原则均来自 002-one-click-deployment 开发周期的实际经验教训

## [一键部署功能] - 2026-04-07

### Added
- 新增单一 Python CLI 部署脚本 `deploy.py`，实现从代码克隆到服务运行的一键部署
- 自动环境检查（Python 3.11+、pip 可用性）
- 自动依赖安装，支持网络中断时最多重试 3 次
- 缺失 `.env` 配置时自动生成模板并暂停，提示用户补全
- 动态端口分配：当 8000 被占用时自动探测并分配下一个可用端口
- 运行中服务检测：重新部署时检测已有 uvicorn 实例并提示用户手动停止
- 部署步骤实时进度输出（`[N/5] ... [OK/FAIL]` 格式）
- 部署失败时输出明确的错误分类、原因和修复建议

### Changed
- 无

### Fixed
- 修复 FR-010 进程冲突检测逻辑：从简单的端口探测改为扫描 `/proc/*/cmdline` 检测已有实例
- 修复 uvicorn host 参数不一致问题，统一使用 `127.0.0.1`
- 修复 proxychains/LD_PRELOAD 环境下端口检测被拦截的问题

### Technical Notes
- 部署脚本仅使用 Python 标准库实现，无额外第三方依赖
- 数据库初始化委托给 FastAPI 应用启动流程（`create_all()`），避免重复实现迁移脚本
- 采用单项目结构，`deploy.py` 作为根目录部署入口，不改动原有 `src/` 和 `tests/` 模块划分
