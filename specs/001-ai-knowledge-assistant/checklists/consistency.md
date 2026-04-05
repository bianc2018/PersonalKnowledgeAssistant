# End-to-End Consistency Checklist: AI 知识管理助手

**Purpose**: 验证 `spec.md`、`plan.md`、`data-model.md`、`contracts/` 与 `quickstart.md` 之间的需求一致性、边界清晰性与覆盖完整性
**Created**: 2026-04-05
**Feature**: [../spec.md](../spec.md)

**Note**: 本清单由 `/speckit.checklist` 生成，聚焦于跨文档需求的端到端一致性校验。

---

## Requirement Completeness

- [ ] CHK001 - 数据模型是否完整覆盖了调研任务队列与并发控制所需的状态和配置实体？当前文档在 Spec §FR-023 与 Plan §Technical Context 中提及队列，但 Data Model 中缺少队列实体定义。 [Gap]
- [ ] CHK002 - 系统配置模型是否完整定义了外部 API 调用配额字段，以支撑调研任务并发上限的需求？Spec §FR-023 要求以配额为并发上限，但 Data Model §2.15 的 `SystemConfig` 未包含配额字段。 [Gap]
- [ ] CHK003 - API 契约是否完整定义了 `awaiting_input` 状态下用户未响应时的超时与自动处理规则？Data Model §5.1 状态机与 Research-API §4 均未明确用户决策等待的超时边界。 [Gap, Spec §FR-006]
- [ ] CHK004 - 需求文档是否完整定义了 RAG 混合检索（向量 + 全文）的合并排序策略与优先级规则？Chat-API §4 提到"合并召回"，但未在 Spec 或 Research §2 中给出可执行的排序或分数融合规则。 [Gap, Spec §FR-003]
- [ ] CHK005 - 系统导出范围是否明确包含了对话历史、调研任务等非知识核心数据的具体处理规则？Spec §FR-010 要求"全部知识及相关元数据"，但 System-API §6 的 ZIP 示例仅展示 `metadata.json` 与 `files/`。 [Gap]

## Requirement Clarity

- [ ] CHK006 - "content 显著变化"触发新版本生成与置信度重新评估的阈值在 Spec、Data Model、API 契约中的定义是否一致且无二义？Knowledge-API §6 提到 "MVP 阶段建议：任何 content 变更均生成新版本"，与 Data Model §2.2、Spec §FR-008 的 ">20% 才生成新版本/重新评估"存在表述差异。 [Consistency, Spec §FR-008, Data Model §2.2, Knowledge-API §6]
- [ ] CHK007 - "每隔一定对话轮次"更新 `UserProfile` 的具体轮次数、触发条件及用户可见性是否在需求中有明确量化？Data Model §2.11 与 Spec §FR-005 均未给出可度量的触发条件。 [Clarity, Spec §FR-005, Data Model §2.11]
- [ ] CHK008 - "端到端查询响应 ≤2 秒"的测量边界（是否包含 LLM 首 token、流式场景 `stream=true` 如何计时）是否在需求中被明确界定？ [Clarity, Spec §SC-005, Plan §Technical Context]
- [ ] CHK009 - "相关元数据"在知识库导出场景中的精确范围（是否包含 Conversation、ResearchTask、SystemConfig 等）是否有清晰的枚举定义？ [Clarity, Spec §FR-010, System-API §6]
- [ ] CHK010 - `version_retention_policy` 的可配置值域（数量/时间/磁盘空间）及其生效后的清理行为是否在需求中被精确描述？Data Model §2.15 中该字段为 `null`，但未说明合法取值与生效规则。 [Clarity, Spec §FR-016, Data Model §2.15]

## Requirement Consistency

- [ ] CHK011 - 知识更新时"任何 `content` 变更均生成新版本"（API 契约建议）与"仅显著变化（>20%）生成新版本"（Data Model）的表述是否存在冲突？ [Conflict, Knowledge-API §6, Data Model §2.2, Spec §FR-008]
- [ ] CHK012 - `llm_config.enable_search`（Research §4 / System-API §4）与 `privacy_settings.allow_web_search`（Spec §FR-015 / System-API §4）以及独立 `search_config` 在外部搜索启停控制上的职责边界是否一致且无冲突？ [Conflict, Spec §FR-015, Research §4, System-API §4, Data Model §2.15]
- [ ] CHK013 - 消息引用结构在 Data Model（`citation_index`）与 Chat API 契约（`index`）中的字段命名是否一致？Chat-API §3 响应示例中使用 `index`，而 Data Model §2.10 定义为 `citation_index`。 [Consistency, Data Model §2.10, Chat-API §3]
- [ ] CHK014 - 调研任务状态机中 `pending_recheck`（Research §10 提到外部服务恢复后自动重新执行）与 Data Model §5.1 中定义的状态枚举（`queued/running/awaiting_input/completed/failed/degraded`）是否存在不一致？ [Conflict, Research §10, Data Model §5.1, Spec §FR-014]
- [ ] CHK015 - 系统重置后"保留空的数据库结构"与初次初始化流程在需求文档中的衔接状态是否一致定义？System-API §8、Spec §FR-025 与 Quickstart §7.2 对重置后是否需要重新调用 `/api/system/init` 的说明存在模糊地带。 [Consistency, System-API §8, Spec §FR-025, Quickstart §7.2]

## Acceptance Criteria Quality

- [ ] CHK016 - 验收标准 SC-002 "90% 的对话查询能够获得相关且准确的回答"是否配备了可操作的评测方法、对齐标准或测试数据集定义？ [Acceptance Criteria, Spec §SC-002]
- [ ] CHK017 - "调研报告在 5 分钟内完成"是否明确了在网络降级、本地模型降级、或人机交互 `awaiting_input` 等待场景下计时是否暂停或排除？ [Acceptance Criteria, Spec §SC-003]
- [ ] CHK018 - 置信度"高/中/低"的分级标准是否能量化为可复现的评分区间或判定规则，以便各实现方得出一致结论？ [Measurability, Spec §SC-004, Data Model §2.7]
- [ ] CHK019 - 配置变更 embedding 模型后，已有 KnowledgeVersion 的向量重新计算触发条件是否在需求中被覆盖？System-API §5 支持修改配置，但 Spec §FR-011 仅在导入场景提及重算。 [Coverage, Gap, System-API §5, Spec §FR-011]

## Scenario Coverage

- [ ] CHK020 - 用户修改单用户密码后，历史备份文件（System-API §6 导出的 ZIP）的解密策略与新旧密钥兼容性是否在需求中被定义？ [Coverage, Gap, Spec §FR-017, System-API §6]
- [ ] CHK021 - 软删除知识条目的附件下载接口行为（是否仍然可用、是否继续占用归档压缩配额）是否在需求中被覆盖？ [Coverage, Spec §FR-021, Knowledge-API §9]
- [ ] CHK022 - 当 `ResearchTask.search_source_used` 为 null（任务失败、被取消或尚未开始检索）时，界面向用户展示当前搜索源类型的要求是否存在替代规范？Data Model §2.12 允许 null，但 Spec §FR-006a 要求展示搜索源。 [Coverage, Gap, Data Model §2.12, Spec §FR-006a]
- [ ] CHK023 - 导出 ZIP 包本身是否需要加密、导出密码与当前系统密码的关联规则是否在需求中被定义？ [Coverage, Gap, Spec §FR-010, System-API §6]

## Edge Case Coverage

- [ ] CHK024 - 用户反复处于 `awaiting_input` 状态（多次决策-resume循环）时任务进度回滚或推进的精确规则是否在需求中被定义？ [Edge Case, Research-API §5, Data Model §5.1]
- [ ] CHK025 - 附件文件提取失败后的"明确提示"要求在 API 响应格式或前端行为中是否有具体的规范定义？Knowledge-API §2 示例仅返回 `extraction_status: failed`，未定义提示规范。 [Edge Case, Spec §FR-001, Knowledge-API §2]
- [ ] CHK026 - 本地 LLM 模式下调研任务的超时和重试策略是否与外部 API 模式保持一致，且在需求中被独立定义？ [Edge Case, Spec §FR-013, Research §10, Data Model §2.15]
- [ ] CHK027 - 导入 ZIP 时 `metadata.json` 版本不兼容或顶层结构校验失败的整体回滚策略（而非单文件跳过）是否在需求中被定义？ [Edge Case, Spec §FR-011, System-API §7]

## Non-Functional Requirements

- [ ] CHK028 - HTTP 爬虫在抓取外部网页时遵守 robots.txt、请求频率限制、User-Agent 声明的伦理与法律边界是否在需求中被明确约束？Plan §Constitution Check 与 Research §4 提及白名单，但 Spec §FR-006a 未将其纳入功能需求。 [Non-Functional, Gap, Spec §FR-006a, Research §4, Plan §Constitution Check]
- [ ] CHK029 - 主密钥在内存中的缓存周期、Session 失效条件、以及服务重启后必须重新鉴权的要求是否在安全需求中被量化？ [Non-Functional, Spec §FR-017, Research §6]
- [ ] CHK030 - `llm_connected: true` 的判定标准（配置存在即视为连接 vs 实时可用性探测）是否在需求中被精确定义？ [Non-Functional, Gap, System-API §3]
- [ ] CHK031 - 调研任务降级至本地模型所需的模型能力基线（如上下文长度、搜索工具支持）是否在需求中作为假设或约束被文档化？ [Assumption, Spec §FR-013, Research §4, Research §7]

## Dependencies & Assumptions

- [ ] CHK032 - 用户"具备基本互联网接入条件"这一假设是否与 Quickstart §8 描述的"完全离线模式"存在潜在冲突或需要补充假设说明？ [Assumption, Spec §Assumptions, Quickstart §8]
- [ ] CHK033 - `retry_settings` 在 Data Model §2.15 中仅包含 `retry_times` 和 `timeout_seconds`，但 Research §10 描述为"指数退避（1s → 2s → 4s）"，配置模型是否遗漏了退避策略参数的定义？ [Gap, Data Model §2.15, Research §10, Spec §FR-022]

## Ambiguities & Conflicts

- [ ] CHK034 - Token 24 小时有效期（System-API §1）与"用户每次访问系统前都必须通过身份验证"（Spec §FR-017）在会话持续性要求上是否存在语义冲突？ [Ambiguity, Spec §FR-017, System-API §1]
- [ ] CHK035 - 归档压缩后（Spec §FR-026）的附件访问行为（实时解压 vs 只读压缩存储）和压缩后磁盘空间计算方式是否存在未定义的行为边界？ [Ambiguity, Spec §FR-026, Data Model §2.15]
- [ ] CHK036 - 多标签"不存在时自动创建"（Knowledge-API §1）与 Data Model §2.4 标签 `name` 的 `UNIQUE` 约束在并发创建场景下的竞争条件是否在需求文档中被免责或处理？ [Ambiguity, Knowledge-API §1, Data Model §2.4]
- [ ] CHK037 - 调研任务"超出配额的任务自动进入队列等待执行"的可视化需求在 API 契约中缺少对应的队列状态查询或队列深度暴露接口，这是否构成需求遗漏？ [Gap, Spec §FR-023, Research-API]
- [ ] CHK038 - 系统重置（System-API §8）后是否需要立即重新调用 `/api/system/init` 才能恢复可用状态，还是重置接口本身即返回初始化就绪状态？完整的后重置状态转换需求是否明确？ [Ambiguity, System-API §8, Spec §FR-025]

## Notes

- 本清单聚焦于**跨文档一致性**，建议逐项澄清后同步更新 `spec.md`、`data-model.md` 与 `contracts/`。
- 高优先级冲突项：CHK011（版本控制策略冲突）、CHK012（搜索开关职责重叠）、CHK014（状态机不一致）、CHK013（字段命名不一致）。
