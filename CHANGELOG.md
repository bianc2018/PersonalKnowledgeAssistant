# Changelog

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
