<!--
Sync Impact Report
Version change: 0.0.0 → 1.0.0
- Initial ratification from template. All placeholders replaced.
- Principles added:
  - 1. 语言统一 (Language Unity)
  - 2. 规划优先 (Plan Before Code)
  - 3. 简洁设计 (Simplicity by Design)
  - 4. Git 纪律 (Git Discipline)
  - 5. 复用优先 (Reuse Over Reinvention)
- Sections added: 安全与质量, 开发工作流, Governance
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (Constitution Check aligned with actual principles)
  - ✅ .specify/templates/spec-template.md (no changes required — already aligned with independent testability)
  - ✅ .specify/templates/tasks-template.md (no changes required — already aligned with story-driven organization)
- Follow-up TODOs: none
-->

# PersonalKnowledgeAssistant Constitution

## Core Principles

### 1. 语言统一 (Language Unity)

所有项目文档、代码注释、提交信息和 AI 交互回复 MUST 使用简体中文。
技术术语（如 API、HTTP、JSON、SQL 等）可保留英文原称。
文档的可读性和一致性优先于逐字翻译的准确性。

**Rationale**: 项目团队以中文为工作语言。统一语言可减少认知负担，
确保所有协作者（包括未来的维护者）能够准确理解设计意图和实现细节。

### 2. 规划优先 (Plan Before Code)

任何功能实现之前 MUST 完成对应的设计规划。
禁止在缺少 spec.md 或 plan.md 的情况下直接编写生产代码。
若需求发生变化，MUST 先更新设计文档，再同步修改实现。

**Rationale**: "先规划，后编码"是项目核心开发习惯。
前期明确的规划能够减少返工，保证用户故事独立可测试，并维护
speckit 驱动的工作流完整性。

### 3. 简洁设计 (Simplicity by Design)

代码和设计 MUST 保持最小必要复杂度。
新增抽象、配置项或依赖库必须有明确的当前需求支撑，
禁止为假设的未来场景引入复杂度（YAGNI）。
当现有工具能够满足需求时，MUST 优先复用而非重新实现。

**Rationale**: 简洁性降低维护成本和理解门槛。
过度设计往往导致不必要的抽象和难以追踪的副作用。
只有在当前需求明确需要时才引入额外复杂度。

### 4. Git 纪律 (Git Discipline)

所有代码和文档变更 MUST 纳入 Git 版本控制。
每次变更确认无误后 SHOULD 立即进行本地提交（`git commit`），
遵循小步提交原则，保持提交粒度合理。
向远程仓库推送（`git push`）MUST 获得用户明确授权后方可执行。

**Rationale**: 小步提交提供了清晰的历史记录和回滚点，
便于代码审查和问题定位。禁止自动推送可防止意外覆盖共享状态。

### 5. 复用优先 (Reuse Over Reinvention)

在引入新依赖或实现新功能前，MUST 评估现有工具和库的可复用性。
优先使用经过验证的现有解决方案，避免重复造轮子。
新增外部依赖 MUST 权衡其维护成本、社区活跃度与学习曲线。

**Rationale**: 成熟的工具和库经过广泛测试，能够节省开发时间
并减少潜在缺陷。对依赖的审慎评估可防止项目陷入"依赖地狱"。

## 安全与质量 (Security and Quality)

- **输入验证**: 所有来自外部的输入（用户请求、配置文件、API 响应）
  在系统边界 MUST 经过验证和清理。
- **漏洞防护**: 实现 MUST 避免引入 OWASP Top 10 中的常见漏洞
  （如 SQL 注入、XSS、命令注入等）。
- **错误处理**: 仅在系统边界和可能发生真实失败的场景添加错误处理逻辑，
  不应对内部不可失败的代码路径进行防御式编程。

## 开发工作流 (Development Workflow)

- **speckit 驱动**: 功能开发遵循 `spec → plan → tasks → implement` 流程。
- **独立测试**: 每个用户故事 MUST 能够独立开发和独立测试。
- **合规检查**: 在 plan.md 的 Constitution Check 阶段，必须对照本章程
  验证当前功能是否违反任何非协商原则。如有违反，MUST 提供明确理由
  并记录在 Complexity Tracking 表格中。

## Governance

本章程的效力高于项目中的所有其他实践指南。
对本章程的任何修订 MUST 满足以下条件：

1. **文档化**: 修订提案 MUST 说明修改原因、影响范围及迁移计划。
2. **版本控制**: 每次修订 MUST 更新 `CONSTITUTION_VERSION`。
   - MAJOR: 删除或重新定义原则，造成治理上的向后不兼容。
   - MINOR: 新增原则或章节，或对现有指导进行实质性扩展。
   - PATCH: 措辞澄清、错别字修正或非语义性微调。
3. **合规审查**: 至少每季度审查一次主要功能 plan.md 的 Constitution Check
   记录，确保本章程持续落地。
4. **运行指导**: 日常开发参考 `.specify/templates/plan-template.md` 中的
   Constitution Check 条款及本仓库的 `CLAUDE.md`。

**Version**: 1.0.0 | **Ratified**: 2026-04-04 | **Last Amended**: 2026-04-04
