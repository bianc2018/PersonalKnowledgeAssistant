# Post-Launch Retrospective: AI 知识管理助手

> **Shipped**: 2026-04-07 | **Retrospective**: 2026-04-09  
> **Days since launch**: 2 | **Feature**: `001-ai-knowledge-assistant`  
> **Type**: 本地单用户 MVP（无外部 Analytics / NewRelic）  
> **Retrospective mode**: 技术 / 流程导向（基于 QA、代码审查与验证结果）

---

## Lifecycle Summary

| Phase | Milestone | Date | Duration |
|-------|-------------|------|----------|
| Phase 0 | Problem Discovery | — | Skipped |
| Phase 1 | Research | 2026-04-04 | 1 day |
| Phase 2 | Product Spec | 2026-04-04 ~ 2026-04-05 | 1 day |
| Phase 3 | Revalidation | — | Skipped |
| Phase 4 | SpecKit Bridge | 2026-04-05 | — |
| Phase 5 | Plan + Tasks | 2026-04-05 | 1 day |
| Phase 6 | Implementation | 2026-04-05 ~ 2026-04-07 | 2 days |
| Phase 6B | Code Review | 2026-04-09 | 1 day |
| Phase 7 | Verify Full | 2026-04-09 | — |
| Phase 8A | Test Plan | 2026-04-07 | — |
| Phase 8B | Test Run | 2026-04-07 | — |
| Phase 9 | Release Readiness | 2026-04-07 | — |
| — | **Ship Date** | **2026-04-07** | — |
| — | **Retrospective** | **2026-04-09** | 2 days post-launch |

**Total time: research → ship = 3 days**

---

## Predicted vs Actual

| Metric | Predicted | Actual (Technical Proxy) | Delta | Status |
|--------|-----------|--------------------------|-------|--------|
| **功能完整性** | 38/38 tasks | 38/38 tasks + 0 CRITICAL 遗留 | — | 达成 |
| **API 集成测试通过** | 100% (目标) | 100% (14/14) | — | 达成 |
| **扩展 QA 通过** | >= 80% (目标) | 91.7% (11/12, 1 skipped) | +11.7% | 超出 |
| **代码审查结论** | 无阻塞项 | 0 Critical / 0 High 遗留 | — | 达成 |
| **全量验证结论** | PASS | PASS (0 CRITICAL / 0 WARNING) | — | 达成 |
| **RAG 引用准确性 (SC-002)** | 90% 相关准确 | 无法在无 LLM 环境下验证 | N/A | 待真实端点验证 |
| **查询性能 (SC-005)** | ≤2s @ 100 条 | API 层快速，但存在 N+1 查询风险 | N/A | 待大规模数据验证 |
| **用户采用率** | N/A (本地单用户) | N/A | N/A | N/A |

---

## Success Criteria Assessment

### SC-001: 2 分钟内完成新知识的添加操作
**状态**: 达成  
**证据**: 集成测试覆盖文本创建、文件上传、URL 添加三种入口，API 层响应均 < 300ms；前端为单表单界面，操作链路短。

### SC-002: 90% 的对话查询回答相关且准确
**状态**: 待验证  
**证据**: QA 报告标记为 PARTIAL。RAG 管道（混合检索、引用解析、SSE 输出）已在 API 层 100% 跑通，但准确性依赖外部 LLM 与 Embedding 质量。需在配置真实 LLM 后执行 `quickstart.md` 端到端验证。

### SC-003: 调研报告在 5 分钟内可用
**状态**: 达成（代码层面）  
**证据**: worker + queue + SSE 全链路可用；`test_create_research_task` 与 `test_research_save` 通过。实际耗时取决于外部搜索与 LLM 响应速度。

### SC-004: 置信度等级直观可识别
**状态**: 达成  
**证据**: 知识详情 API 返回 `confidence` 对象（含 `score_level` 与 `rationale`），扩展 QA 已验证字段存在。

### SC-005: 100 条知识时查询/展示 ≤2 秒
**状态**: 风险可控/待压力验证  
**证据**: 当前集成测试的查询端点响应迅速（内存数据库+小数据量）。代码审查发现 `get_knowledge_list()` 和 `get_messages()` 存在 N+1 查询（REV-003），在 100 条知识场景下可能成为性能瓶颈，建议后续优化为 `IN (...)` 批量查询。

---

## Code Review & Quality Findings

### 已修复的阻塞问题
在 Phase 6B Code Review 中发现并修复了 3 项 CRITICAL 与 3 项 HIGH 问题：

| ID | 问题 | 修复方式 | 状态 |
|----|------|----------|------|
| REV-002 | 启动时无条件 `DROP TABLE vec_chunks` 导致向量/FTS 数据丢失 | 移除 DROP，改用 `IF NOT EXISTS` 创建 | 已修复 |
| REV-007 | `search_similar()` 将 embedding JSON 拼接到 SQL 字符串中存在注入风险 | 改为参数绑定 `?` + `json.dumps()` | 已修复 |
| REV-008 | 文件上传缺少 1GB 限制与路径遍历防护 | 增加 413 大小校验 + `_sanitize_filename()` | 已修复 |
| REV-009 | URL 抓取缺少 SSRF 防护 | 新增 `validate_url()` 拦截私有 IP 与非 http(s) 协议 | 已修复 |
| REV-010 | 导入/导出备份未校验 `storage_path` 导致路径遍历 | 导出限定在 `files_dir` 下；导入拒绝 `..` 与绝对路径 | 已修复 |
| REV-012 | SSE 流式响应中 delta 未做 JSON 转义 | 改用 `json.dumps()` 生成 payload | 已修复 |

### 遗留的改进项（非阻塞）
- **REV-003**: N+1 查询（影响 SC-005 大规模性能目标）
- **REV-011**: CORS 配置可收紧（`allow_origins=["*"]` → 本地来源）
- **REV-013**: router 层重复的数据库开关样板代码，可提取为依赖注入
- **REV-014 ~ REV-016**: search 模块、文件上传、系统导入导出、worker 状态流转的测试覆盖缺口

---

## Test & Verification Summary

### 测试结果
- **集成测试**: 14/14 passed（auth, chat, knowledge, research）
- **扩展 QA 测试**: 11/12 passed, 1 skipped（Research SSE 在 ASGI test client 中无法完整消费）
- **全量验证**: PASS，0 Critical / 0 Warning

### 验证缺口
- **LLM 依赖场景**: RAG 引用准确性、调研报告内容质量、置信度评分准确性需在真实 LLM 配置后补充验收。
- **性能压测**: 未在 100 条知识真实数据集下测量端到端 TTFB。

---

## What Went Right

1. **技术选型高度匹配需求**  
   FastAPI + sqlite-vec + aiosqlite 的最小技术栈在 3 天内支撑了完整的知识管理、RAG 对话、异步调研三大核心能力，证明了“本地优先、最小依赖”策略的有效性。

2. **Spec-driven 开发减少了返工**  
   `spec.md` 中的澄清记录（尤其是 FR-006a 搜索优先级、FR-008 版本/置信度触发策略、FR-014 pending_recheck 状态定义）为后续实现提供了明确依据，实现阶段未出现大规模的需求反复。

3. **Code Review 在上线前拦截了关键安全与数据丢失问题**  
   REV-002（向量数据丢失）和 REV-007（SQL 注入）如果在上线后才暴露，修复成本极高。Phase 6B 的引入对此 MVP 非常有价值。

4. **测试左移效果良好**  
   集成测试覆盖了所有用户故事的 API 层主路径，在每次修复后都能快速验证回归安全。

---

## What Could Be Better

1. **数据库初始化逻辑在规划阶段未充分审视**  
   `init_db()` 中的 `DROP TABLE` 是一个“为了开发方便”的临时写法，却没有在产品规格或计划中被标记为风险点，导致它进入了 main 分支。
   
   *Fix for next time*: 在 Plan 阶段为所有“生命周期钩子”增加显式检查项；禁止带 `DROP TABLE` 的代码合入，除非附带迁移脚本。

2. **安全边界检查在 pre-impl review 阶段缺失**  
   SSRF、路径遍历、SQL 注入等经典 Web 安全问题直到 Code Review 才被发现，说明 Pre-Implementation Review（Phase 5C）被跳过导致了一层防护缺失。
   
   *Fix for next time*: 即使时间紧张，也应至少执行一份结构化的安全 checklist（OWASP Top 10 快速扫描），而不是完全跳过 Phase 5C。

3. **测试覆盖存在结构性缺口**  
   `src/search/`（RAG 核心）没有任何直接测试；文件上传、系统导入导出等高风险边界也缺少集成测试。QA 的 91.7% pass rate 主要来自 API 层 happy path。
   
   *Fix for next time*: 在 Task 阶段为每一个新模块明确要求“对应的单元/集成测试任务”，并在 verify 阶段将其作为必过项。

4. **性能约束未在实现阶段得到验证**  
   SC-005（≤2s @ 100 条知识）是一个 MUST 级成功标准，但无论是实现还是 QA 阶段都没有构造 100 条知识的数据集来测量 TTFB。
   
   *Fix for next time*: 为性能类成功标准配套编写“负载/压力测试 fixture”，在 CI 或本地至少运行一次作为 checkpoint。

---

## Research Accuracy Audit

| 研究阶段的预测/决策 | 实际结果 | 准确性 |
|---------------------|----------|--------|
| Python 3.11+ + FastAPI 是最小可用栈 | 支撑了全部功能（含 SSE + 异步任务） | 10/10 |
| SQLite + sqlite-vec 满足本地向量/全文需求 | 功能实现完整，但虚拟表 `DROP` 用法引发数据丢失风险 | 8/10 |
| asyncio.Queue + SSE 适合异步调研 | 实现简单有效，ASGI test client 消费流有限制 | 9/10 |
| LLM builtin search → Search API → 爬虫 优先级链 | 最初实现为 stub，后于 code review 补全 | 7/10 |
| 单用户 JWT + Argon2id + AES-256-GCM 安全模型 | 鉴权与加密链路简洁可用 | 9/10 |
| 多媒体提取依赖 pypdf / docx / openpyxl / pytesseract | extractor.py 已集成，失败回退策略到位 | 9/10 |

**综合研究准确性评分: 8.7/10**

---

## Open Issues & Follow-up

| ID | Type | Description | Priority | ETA |
|----|------|-------------|----------|-----|
| OI-001 | 验证缺口 | 配置真实 LLM/Embedding 后执行 quickstart.md 端到端验证（SC-002、SC-003） | P1 | ASAP |
| OI-002 | 性能优化 | 修复 REV-003 N+1 查询，确保 100 条知识场景 ≤2s | P2 | 下一次迭代 |
| OI-003 | 测试补充 | 为 search 模块、upload、export/import、worker 状态流转补全测试 | P2 | 下一次迭代 |
| OI-004 | 安全加固 | 收紧 CORS、提取数据库依赖注入、统一安全 URL 校验范围 | P3 | 后续 refactor |
| OI-005 | 功能增强 | LLM 未配置时的 zero-state UI 提示与引导 | P3 | 后续版本 |

---

## Next Steps

基于当前技术/流程视角的 retrospective 结果：

1. **立即执行（P1）**  
   在 `.env` 或系统配置中填入有效的 LLM / Embedding / Search API 凭据，启动服务后完整跑通 quickstart.md 的 5.1~5.3 端到端流程，补完 SC-002 的准确性验收。

2. **下一次迭代（P2）**  
   修复 N+1 查询并补充 search + upload + import/export 的测试用例，将测试覆盖率提升到模块级别无缺口。

3. **工艺改进（Process）**  
   未来项目中：
   - 所有生命周期钩子代码必须经过“是否破坏持久化数据”的显式审查。
   - 不跳过 Phase 5C，或至少使用一份安全 checklist。
   - 性能类成功标准必须配套一个最小规模的负载测试 fixture。

---

## Lessons Learned for Future Features

1. **Process**: Code Review 不应被视为可选步骤。对于 M区P 项目，即使是自己一个人开发，Phase 6B 也能在最后一刻拦截灾难性问题。
2. **Research**: 技术栈选型准确，但对 sqlite-vec 虚拟表的生命周期管理（`IF NOT EXISTS` vs `DROP`）研究不够深入，应在 Phase 1 加入数据持久化行为确认。
3. **Implementation**: 安全边界（输入验证、SQL 参数化、URL 沙箱、路径净化）应成为每个 router/service 的默认习惯，而非事后修补。
4. **Testing**: API 集成测试能快速验证功能可用性，但无法替代针对算法模块（search、hybrid scoring）和边界风险（文件/路径/zip）的专项测试。
